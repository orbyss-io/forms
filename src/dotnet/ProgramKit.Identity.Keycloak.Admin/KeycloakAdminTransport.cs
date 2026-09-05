using System.Globalization;
using System.Net;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Sends authenticated, bounded requests to one Keycloak realm's Admin REST API.</summary>
internal sealed class KeycloakAdminTransport(
    IHttpClientFactory httpClientFactory,
    IOptions<KeycloakAdminOptions> options,
    TimeProvider timeProvider) : IDisposable
{
    /// <summary>Names the isolated HTTP client used for Keycloak administration.</summary>
    internal const string HttpClientName = "ProgramKit.Identity.Keycloak.Admin";
    /// <summary>Applies interoperable web JSON naming and parsing conventions.</summary>
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    /// <summary>Coalesces concurrent service-account token refreshes.</summary>
    private readonly SemaphoreSlim tokenLock = new(1, 1);
    /// <summary>Holds the current safely bounded service-account access token.</summary>
    private AccessToken? token;

    /// <summary>Sends an authenticated Admin REST request and returns its optional JSON representation.</summary>
    public async ValueTask<JsonElement?> SendAsync(
        HttpMethod method,
        string relativePath,
        object? body = null,
        CancellationToken cancellationToken = default)
    {
        var configured = options.Value;
        var uri = $"{configured.ServerUrl.TrimEnd('/')}/admin/realms/{Escape(configured.Realm)}/{relativePath.TrimStart('/')}";
        using var request = new HttpRequestMessage(method, uri);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", await GetTokenAsync(cancellationToken).ConfigureAwait(false));
        if (body is not null)
        {
            request.Content = new StringContent(JsonSerializer.Serialize(body, JsonOptions), Encoding.UTF8, "application/json");
        }
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(configured.TimeoutSeconds));
        using var response = await httpClientFactory.CreateClient(HttpClientName)
            .SendAsync(request, HttpCompletionOption.ResponseHeadersRead, timeout.Token)
            .ConfigureAwait(false);
        if (response.StatusCode == HttpStatusCode.NotFound && method == HttpMethod.Get)
        {
            return null;
        }
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(
                $"Keycloak Admin REST {method} {relativePath} returned HTTP {(int)response.StatusCode}.",
                null,
                response.StatusCode);
        }
        if (response.Content.Headers.ContentLength == 0 || response.StatusCode == HttpStatusCode.NoContent)
        {
            return null;
        }
        await using var stream = await response.Content.ReadAsStreamAsync(timeout.Token).ConfigureAwait(false);
        using var document = await JsonDocument.ParseAsync(stream, cancellationToken: timeout.Token).ConfigureAwait(false);
        return document.RootElement.Clone();
    }

    /// <summary>Creates a resource and extracts its stable identifier from the response location.</summary>
    public async ValueTask<string> CreateAsync(
        string relativePath,
        object body,
        CancellationToken cancellationToken = default)
    {
        var configured = options.Value;
        var uri = $"{configured.ServerUrl.TrimEnd('/')}/admin/realms/{Escape(configured.Realm)}/{relativePath.TrimStart('/')}";
        using var request = new HttpRequestMessage(HttpMethod.Post, uri);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", await GetTokenAsync(cancellationToken).ConfigureAwait(false));
        request.Content = new StringContent(JsonSerializer.Serialize(body, JsonOptions), Encoding.UTF8, "application/json");
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(TimeSpan.FromSeconds(configured.TimeoutSeconds));
        using var response = await httpClientFactory.CreateClient(HttpClientName).SendAsync(request, timeout.Token).ConfigureAwait(false);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"Keycloak Admin REST POST {relativePath} returned HTTP {(int)response.StatusCode}.", null, response.StatusCode);
        }
        var location = response.Headers.Location?.Segments.LastOrDefault()?.Trim('/');
        if (string.IsNullOrWhiteSpace(location))
        {
            throw new InvalidDataException($"Keycloak Admin REST POST {relativePath} did not return a resource Location.");
        }
        return Uri.UnescapeDataString(location);
    }

    /// <summary>Disposes the token-refresh synchronization primitive.</summary>
    public void Dispose() => tokenLock.Dispose();

    /// <summary>Escapes one untrusted Admin REST path or query value.</summary>
    internal static string Escape(string value) => Uri.EscapeDataString(value);

    /// <summary>Gets a safely cached service-account token or acquires a new one.</summary>
    private async ValueTask<string> GetTokenAsync(CancellationToken cancellationToken)
    {
        var configured = options.Value;
        if (token is { } cached && cached.ExpiresAt > timeProvider.GetUtcNow().AddSeconds(configured.RefreshBeforeExpirySeconds))
        {
            return cached.Value;
        }
        await tokenLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (token is { } locked && locked.ExpiresAt > timeProvider.GetUtcNow().AddSeconds(configured.RefreshBeforeExpirySeconds))
            {
                return locked.Value;
            }
            var endpoint = $"{configured.ServerUrl.TrimEnd('/')}/realms/{Escape(configured.AdminRealm)}/protocol/openid-connect/token";
            using var request = new HttpRequestMessage(HttpMethod.Post, endpoint);
            var encoded = $"{FormEncode(configured.ClientId)}:{FormEncode(configured.ClientSecret)}";
            request.Headers.Authorization = new AuthenticationHeaderValue("Basic", Convert.ToBase64String(Encoding.UTF8.GetBytes(encoded)));
            request.Content = new FormUrlEncodedContent([new("grant_type", "client_credentials")]);
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(TimeSpan.FromSeconds(configured.TimeoutSeconds));
            using var response = await httpClientFactory.CreateClient(HttpClientName).SendAsync(request, timeout.Token).ConfigureAwait(false);
            if (!response.IsSuccessStatusCode)
            {
                throw new HttpRequestException($"Keycloak service-account token endpoint returned HTTP {(int)response.StatusCode}.", null, response.StatusCode);
            }
            await using var stream = await response.Content.ReadAsStreamAsync(timeout.Token).ConfigureAwait(false);
            using var document = await JsonDocument.ParseAsync(stream, cancellationToken: timeout.Token).ConfigureAwait(false);
            var root = document.RootElement;
            var value = root.GetProperty("access_token").GetString();
            var expires = root.GetProperty("expires_in").ValueKind switch
            {
                JsonValueKind.Number => root.GetProperty("expires_in").GetInt32(),
                JsonValueKind.String => int.Parse(root.GetProperty("expires_in").GetString()!, CultureInfo.InvariantCulture),
                _ => 0
            };
            if (string.IsNullOrWhiteSpace(value) || expires <= 0)
            {
                throw new InvalidDataException("The Keycloak token response did not contain a valid access_token and expires_in.");
            }
            token = new(value, timeProvider.GetUtcNow().AddSeconds(expires));
            return value;
        }
        finally
        {
            tokenLock.Release();
        }
    }

    /// <summary>Applies OAuth form encoding to one client credential.</summary>
    private static string FormEncode(string value) => Uri.EscapeDataString(value).Replace("%20", "+", StringComparison.Ordinal);
}
