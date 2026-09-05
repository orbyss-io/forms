using System.Globalization;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.TokenExchange;

/// <summary>Performs standards-based OAuth token exchange without provider coupling.</summary>
internal sealed class TokenExchangeService(
    IHttpClientFactory httpClientFactory,
    IOptions<TokenExchangeOptions> options,
    TimeProvider timeProvider) : ITokenExchangeService
{
    /// <summary>Names the isolated HTTP client used for token-exchange traffic.</summary>
    internal const string HttpClientName = "ProgramKit.Authentication.TokenExchange";

    /// <inheritdoc />
    public async ValueTask<TokenExchangeResult> ExchangeAsync(
        string registration,
        TokenExchangeRequest request,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(registration);
        ArgumentNullException.ThrowIfNull(request);
        ValidateRequest(request);
        if (!options.Value.Registrations.TryGetValue(registration, out var settings))
        {
            throw new InvalidOperationException($"OAuth token-exchange registration '{registration}' is not configured.");
        }

        using var message = CreateMessage(settings, request);
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(settings.TimeoutSeconds));
        using var response = await httpClientFactory.CreateClient(HttpClientName)
            .SendAsync(message, HttpCompletionOption.ResponseHeadersRead, timeout.Token)
            .ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(
                $"The OAuth token-exchange endpoint returned HTTP {(int)response.StatusCode}.",
                null,
                response.StatusCode);
        }

        await using var stream = await response.Content.ReadAsStreamAsync(timeout.Token).ConfigureAwait(false);
        using var document = await JsonDocument.ParseAsync(stream, cancellationToken: timeout.Token).ConfigureAwait(false);
        return ReadResult(document.RootElement);
    }

    /// <summary>Validates paired actor fields and exact RFC request values before any I/O.</summary>
    private static void ValidateRequest(TokenExchangeRequest request)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(request.SubjectToken);
        RequireAbsoluteUri(request.SubjectTokenType, nameof(request.SubjectTokenType));
        RequireAbsoluteUri(request.RequestedTokenType, nameof(request.RequestedTokenType));
        if ((request.ActorToken is null) != (request.ActorTokenType is null))
        {
            throw new ArgumentException("ActorToken and ActorTokenType must be supplied together.", nameof(request));
        }

        if (request.ActorToken is not null)
        {
            ArgumentException.ThrowIfNullOrWhiteSpace(request.ActorToken);
            RequireAbsoluteUri(request.ActorTokenType!, nameof(request.ActorTokenType));
        }

        if (request.Scopes.Any(scope => string.IsNullOrWhiteSpace(scope) || scope.Any(char.IsWhiteSpace)))
        {
            throw new ArgumentException("Scopes must contain non-empty individual OAuth scope values.", nameof(request));
        }

        if (request.Resource is not null
            && (!Uri.TryCreate(request.Resource, UriKind.Absolute, out var resource)
                || (resource.Scheme != Uri.UriSchemeHttps && resource.Scheme != Uri.UriSchemeHttp)))
        {
            throw new ArgumentException("Resource must be an absolute HTTP or HTTPS URI.", nameof(request));
        }
    }

    /// <summary>Creates one authenticated RFC 8693 form request.</summary>
    private static HttpRequestMessage CreateMessage(
        TokenExchangeRegistration registration,
        TokenExchangeRequest exchange)
    {
        var message = new HttpRequestMessage(HttpMethod.Post, registration.TokenEndpoint);
        var fields = new List<KeyValuePair<string, string>>
        {
            new("grant_type", "urn:ietf:params:oauth:grant-type:token-exchange"),
            new("subject_token", exchange.SubjectToken),
            new("subject_token_type", exchange.SubjectTokenType),
            new("requested_token_type", exchange.RequestedTokenType)
        };
        Add(fields, "audience", exchange.Audience);
        Add(fields, "resource", exchange.Resource);
        if (exchange.Scopes.Length > 0)
        {
            fields.Add(new("scope", string.Join(' ', exchange.Scopes)));
        }
        Add(fields, "actor_token", exchange.ActorToken);
        Add(fields, "actor_token_type", exchange.ActorTokenType);

        if (registration.ClientAuthenticationMethod == "client_secret_basic")
        {
            var credentials = $"{FormEncode(registration.ClientId)}:{FormEncode(registration.ClientSecret)}";
            message.Headers.Authorization = new AuthenticationHeaderValue(
                "Basic",
                Convert.ToBase64String(Encoding.UTF8.GetBytes(credentials)));
        }
        else
        {
            fields.Add(new("client_id", registration.ClientId));
            fields.Add(new("client_secret", registration.ClientSecret));
        }

        message.Content = new FormUrlEncodedContent(fields);
        return message;
    }

    /// <summary>Projects a successful standard token-exchange response.</summary>
    private TokenExchangeResult ReadResult(JsonElement root)
    {
        var accessToken = RequiredString(root, "access_token");
        var issuedTokenType = RequiredString(root, "issued_token_type");
        var tokenType = RequiredString(root, "token_type");
        DateTimeOffset? expiresAt = null;
        if (root.TryGetProperty("expires_in", out var lifetime))
        {
            var seconds = lifetime.ValueKind switch
            {
                JsonValueKind.Number when lifetime.TryGetInt32(out var number) => number,
                JsonValueKind.String when int.TryParse(
                    lifetime.GetString(),
                    NumberStyles.None,
                    CultureInfo.InvariantCulture,
                    out var number) => number,
                _ => 0
            };
            if (seconds <= 0)
            {
                throw new InvalidDataException("The OAuth token-exchange expires_in value must be positive.");
            }
            expiresAt = timeProvider.GetUtcNow().AddSeconds(seconds);
        }

        var scopes = root.TryGetProperty("scope", out var scope) && scope.ValueKind == JsonValueKind.String
            ? scope.GetString()!.Split(' ', StringSplitOptions.RemoveEmptyEntries)
            : [];
        return new TokenExchangeResult(accessToken, issuedTokenType, tokenType, expiresAt, scopes);
    }

    /// <summary>Adds a non-empty optional form field.</summary>
    private static void Add(ICollection<KeyValuePair<string, string>> fields, string name, string? value)
    {
        if (!string.IsNullOrWhiteSpace(value))
        {
            fields.Add(new(name, value));
        }
    }

    /// <summary>Requires an absolute URI token-type identifier.</summary>
    private static void RequireAbsoluteUri(string value, string name)
    {
        if (!Uri.TryCreate(value, UriKind.Absolute, out _))
        {
            throw new ArgumentException("Token types must be absolute URI identifiers.", name);
        }
    }

    /// <summary>Reads one required non-empty string from a successful response.</summary>
    private static string RequiredString(JsonElement root, string property)
    {
        if (!root.TryGetProperty(property, out var value)
            || value.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(value.GetString()))
        {
            throw new InvalidDataException($"The OAuth token-exchange response omitted {property}.");
        }
        return value.GetString()!;
    }

    /// <summary>Encodes a client credential for the OAuth HTTP Basic convention.</summary>
    private static string FormEncode(string value) =>
        Uri.EscapeDataString(value).Replace("%20", "+", StringComparison.Ordinal);
}
