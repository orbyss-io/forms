using System.Text.Json;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Implements explicitly high-privilege Keycloak realm operations.</summary>
internal sealed class KeycloakRealmOperations(KeycloakAdminTransport transport) : IKeycloakRealmOperations
{
    /// <inheritdoc />
    public async ValueTask<JsonElement> GetKeyMetadataAsync(CancellationToken cancellationToken = default) => await RequiredAsync(HttpMethod.Get, "keys", null, cancellationToken);
    /// <inheritdoc />
    public async ValueTask<JsonElement> GetEventConfigurationAsync(CancellationToken cancellationToken = default) => await RequiredAsync(HttpMethod.Get, "events/config", null, cancellationToken);
    /// <inheritdoc />
    public async ValueTask UpdateEventConfigurationAsync(JsonElement configuration, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Put, "events/config", configuration, cancellationToken);
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<JsonElement>> GetEventsAsync(int first = 0, int maximum = 100, CancellationToken cancellationToken = default) => KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, $"events?first={first}&max={maximum}", cancellationToken: cancellationToken), static item => item.Clone());
    /// <inheritdoc />
    public async ValueTask DeleteEventsAsync(CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Delete, "events", cancellationToken: cancellationToken);
    /// <inheritdoc />
    public async ValueTask ClearUserLoginFailuresAsync(string userId, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Delete, $"attack-detection/brute-force/users/{KeycloakAdminTransport.Escape(userId)}", cancellationToken: cancellationToken);
    /// <inheritdoc />
    public async ValueTask ClearAllLoginFailuresAsync(CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Delete, "attack-detection/brute-force/users", cancellationToken: cancellationToken);
    /// <summary>Requires a representation from an endpoint that cannot validly return an empty response.</summary>
    private async ValueTask<JsonElement> RequiredAsync(HttpMethod method, string path, object? body, CancellationToken cancellationToken) => await transport.SendAsync(method, path, body, cancellationToken) ?? throw new InvalidDataException($"Keycloak returned no representation for {path}.");
}
