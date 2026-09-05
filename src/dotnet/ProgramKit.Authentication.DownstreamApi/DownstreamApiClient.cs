using System.Net.Http.Headers;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using ProgramKit.Authentication.ClientCredentials;
using ProgramKit.Authentication.TokenExchange;

namespace ProgramKit.Authentication.DownstreamApi;

/// <summary>Routes authenticated calls only to fixed configured downstream destinations.</summary>
internal sealed class DownstreamApiClient(
    IHttpClientFactory httpClientFactory,
    IOptions<DownstreamApiOptions> options,
    IServiceProvider services,
    ICurrentAccessTokenAccessor currentAccessToken) : IDownstreamApiClient
{
    /// <summary>Names the isolated non-redirecting downstream HTTP client.</summary>
    internal const string HttpClientName = "ProgramKit.Authentication.DownstreamApi";

    /// <inheritdoc />
    public async ValueTask<HttpResponseMessage> SendAsync(
        string registration,
        HttpRequestMessage request,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(registration);
        ArgumentNullException.ThrowIfNull(request);
        if (!options.Value.Registrations.TryGetValue(registration, out var settings))
        {
            throw new InvalidOperationException($"Downstream API registration '{registration}' is not configured.");
        }
        ValidateRelativeRequest(request);
        var (scheme, token) = settings.AccessMode switch
        {
            "ClientCredentials" => await GetClientCredentialsAsync(settings, cancellationToken).ConfigureAwait(false),
            "TokenExchange" => await GetExchangedTokenAsync(settings, cancellationToken).ConfigureAwait(false),
            _ => throw new InvalidOperationException(
                $"Downstream API registration '{registration}' has unsupported mode '{settings.AccessMode}'.")
        };
        request.RequestUri = new Uri(new Uri(settings.BaseAddress, UriKind.Absolute), request.RequestUri!);
        request.Headers.Authorization = new AuthenticationHeaderValue(scheme, token);
        return await httpClientFactory.CreateClient(HttpClientName)
            .SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken)
            .ConfigureAwait(false);
    }

    /// <summary>Acquires an application-only access token from the selected machine registration.</summary>
    private async ValueTask<(string Scheme, string Token)> GetClientCredentialsAsync(
        DownstreamApiRegistration settings,
        CancellationToken cancellationToken)
    {
        var provider = services.GetService<IClientCredentialsTokenProvider>()
            ?? throw new InvalidOperationException(
                "ClientCredentials mode requires the ProgramKit.Authentication.ClientCredentials feature in this shell.");
        var token = await provider.GetTokenAsync(settings.TokenRegistration, cancellationToken).ConfigureAwait(false);
        return (token.TokenType, token.Value);
    }

    /// <summary>Exchanges the current validated user token for a downscoped downstream token.</summary>
    private async ValueTask<(string Scheme, string Token)> GetExchangedTokenAsync(
        DownstreamApiRegistration settings,
        CancellationToken cancellationToken)
    {
        var exchange = services.GetService<ITokenExchangeService>()
            ?? throw new InvalidOperationException(
                "TokenExchange mode requires the ProgramKit.Authentication.TokenExchange feature in this shell.");
        var subject = await currentAccessToken.GetRequiredTokenAsync(cancellationToken).ConfigureAwait(false);
        var token = await exchange.ExchangeAsync(
            settings.TokenRegistration,
            new TokenExchangeRequest
            {
                SubjectToken = subject,
                Audience = settings.Audience,
                Resource = settings.Resource,
                Scopes = settings.Scopes
            },
            cancellationToken).ConfigureAwait(false);
        return (token.TokenType, token.AccessToken);
    }

    /// <summary>Rejects caller-selected destinations, parent traversal, and caller-owned authorization.</summary>
    private static void ValidateRelativeRequest(HttpRequestMessage request)
    {
        var target = request.RequestUri;
        if (target is null || target.IsAbsoluteUri || target.OriginalString.StartsWith("/", StringComparison.Ordinal))
        {
            throw new ArgumentException("Downstream requests must use a non-rooted relative URI.", nameof(request));
        }
        if (target.OriginalString.Split('/', StringSplitOptions.RemoveEmptyEntries).Contains("..", StringComparer.Ordinal))
        {
            throw new ArgumentException("Downstream request paths must not contain parent traversal.", nameof(request));
        }
        if (request.Headers.Authorization is not null)
        {
            throw new ArgumentException("Downstream authorization is owned by Program Kit.", nameof(request));
        }
    }
}
