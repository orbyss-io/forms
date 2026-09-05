using System.Collections.Concurrent;
using System.Globalization;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.ClientCredentials;

/// <summary>Acquires and caches named OAuth client-credentials tokens.</summary>
internal sealed class ClientCredentialsTokenProvider(
    IHttpClientFactory httpClientFactory,
    IOptions<ClientCredentialsOptions> options,
    TimeProvider timeProvider) : IClientCredentialsTokenProvider, IDisposable
{
    /// <summary>Names the isolated HTTP client used for token-endpoint traffic.</summary>
    internal const string HttpClientName = "ProgramKit.Authentication.ClientCredentials";

    /// <summary>Holds the most recent bounded token for each registration.</summary>
    private readonly ConcurrentDictionary<string, OAuthAccessToken> cache = new(StringComparer.Ordinal);

    /// <summary>Coalesces concurrent refreshes independently for each registration.</summary>
    private readonly ConcurrentDictionary<string, SemaphoreSlim> locks = new(StringComparer.Ordinal);

    /// <inheritdoc />
    public async ValueTask<OAuthAccessToken> GetTokenAsync(
        string registration,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(registration);
        var settings = GetRegistration(registration);
        if (TryGetUsableToken(registration, settings, out var cached))
        {
            return cached;
        }

        var refreshLock = locks.GetOrAdd(registration, static _ => new SemaphoreSlim(1, 1));
        await refreshLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (TryGetUsableToken(registration, settings, out cached))
            {
                return cached;
            }

            var acquired = await AcquireAsync(settings, cancellationToken).ConfigureAwait(false);
            cache[registration] = acquired;
            return acquired;
        }
        finally
        {
            refreshLock.Release();
        }
    }

    /// <inheritdoc />
    public void Dispose()
    {
        foreach (var refreshLock in locks.Values)
        {
            refreshLock.Dispose();
        }
    }

    /// <summary>Resolves an exact configured registration or fails without fallback.</summary>
    private ClientCredentialsRegistration GetRegistration(string name)
    {
        if (!options.Value.Registrations.TryGetValue(name, out var registration))
        {
            throw new InvalidOperationException($"OAuth client-credentials registration '{name}' is not configured.");
        }

        return registration;
    }

    /// <summary>Returns a cached token only while it remains outside its refresh window.</summary>
    private bool TryGetUsableToken(
        string name,
        ClientCredentialsRegistration registration,
        out OAuthAccessToken token)
    {
        if (cache.TryGetValue(name, out var candidate)
            && candidate.ExpiresAt > timeProvider.GetUtcNow().AddSeconds(registration.RefreshBeforeExpirySeconds))
        {
            token = candidate;
            return true;
        }

        token = null!;
        return false;
    }

    /// <summary>Performs one bounded OAuth client-credentials request.</summary>
    private async Task<OAuthAccessToken> AcquireAsync(
        ClientCredentialsRegistration registration,
        CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, registration.TokenEndpoint);
        var fields = new List<KeyValuePair<string, string>>
        {
            new("grant_type", "client_credentials")
        };
        if (registration.Scopes.Length > 0)
        {
            fields.Add(new("scope", string.Join(' ', registration.Scopes)));
        }

        if (registration.ClientAuthenticationMethod == "client_secret_basic")
        {
            var credentials = $"{FormEncode(registration.ClientId)}:{FormEncode(registration.ClientSecret)}";
            request.Headers.Authorization = new AuthenticationHeaderValue(
                "Basic",
                Convert.ToBase64String(Encoding.UTF8.GetBytes(credentials)));
        }
        else
        {
            fields.Add(new("client_id", registration.ClientId));
            fields.Add(new("client_secret", registration.ClientSecret));
        }

        request.Content = new FormUrlEncodedContent(fields);
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(registration.TimeoutSeconds));
        using var response = await httpClientFactory.CreateClient(HttpClientName)
            .SendAsync(request, HttpCompletionOption.ResponseHeadersRead, timeout.Token)
            .ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(
                $"The OAuth client-credentials token endpoint returned HTTP {(int)response.StatusCode}.",
                null,
                response.StatusCode);
        }

        await using var stream = await response.Content.ReadAsStreamAsync(timeout.Token).ConfigureAwait(false);
        using var document = await JsonDocument.ParseAsync(stream, cancellationToken: timeout.Token).ConfigureAwait(false);
        var root = document.RootElement;
        var value = RequiredString(root, "access_token");
        var tokenType = RequiredString(root, "token_type");
        var expiresIn = ReadExpiresIn(root);
        return new OAuthAccessToken(value, tokenType, timeProvider.GetUtcNow().AddSeconds(expiresIn));
    }

    /// <summary>Reads one required non-empty string from a successful token response.</summary>
    private static string RequiredString(JsonElement root, string property)
    {
        if (!root.TryGetProperty(property, out var value)
            || value.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(value.GetString()))
        {
            throw new InvalidDataException($"The OAuth token response did not contain a non-empty {property} value.");
        }

        return value.GetString()!;
    }

    /// <summary>Reads the positive OAuth expires-in lifetime in its interoperable number or string form.</summary>
    private static int ReadExpiresIn(JsonElement root)
    {
        if (!root.TryGetProperty("expires_in", out var value))
        {
            throw new InvalidDataException("The OAuth token response did not contain expires_in.");
        }

        var seconds = value.ValueKind switch
        {
            JsonValueKind.Number when value.TryGetInt32(out var number) => number,
            JsonValueKind.String when int.TryParse(
                value.GetString(),
                NumberStyles.None,
                CultureInfo.InvariantCulture,
                out var number) => number,
            _ => 0
        };
        if (seconds <= 0)
        {
            throw new InvalidDataException("The OAuth token response expires_in value must be a positive integer.");
        }

        return seconds;
    }

    /// <summary>Encodes a client credential for the OAuth HTTP Basic convention.</summary>
    private static string FormEncode(string value) =>
        Uri.EscapeDataString(value).Replace("%20", "+", StringComparison.Ordinal);
}
