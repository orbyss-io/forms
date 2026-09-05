using System.Text.Json;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Implements Keycloak-specific organization administration.</summary>
internal sealed class KeycloakOrganizationAdministration(KeycloakAdminTransport transport) : IKeycloakOrganizationAdministration
{
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<JsonElement>> FindAsync(string? search = null, int first = 0, int maximum = 100, CancellationToken cancellationToken = default)
    {
        var path = $"organizations?first={first}&max={maximum}" + (string.IsNullOrWhiteSpace(search) ? string.Empty : $"&search={KeycloakAdminTransport.Escape(search)}");
        return KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, path, cancellationToken: cancellationToken), static item => item.Clone());
    }
    /// <inheritdoc />
    public async ValueTask<JsonElement?> GetAsync(string organizationId, CancellationToken cancellationToken = default) => await transport.SendAsync(HttpMethod.Get, $"organizations/{KeycloakAdminTransport.Escape(organizationId)}", cancellationToken: cancellationToken);
    /// <inheritdoc />
    public ValueTask<string> CreateAsync(JsonElement representation, CancellationToken cancellationToken = default) => transport.CreateAsync("organizations", representation, cancellationToken);
    /// <inheritdoc />
    public async ValueTask UpdateAsync(string organizationId, JsonElement representation, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Put, $"organizations/{KeycloakAdminTransport.Escape(organizationId)}", representation, cancellationToken);
    /// <inheritdoc />
    public async ValueTask DeleteAsync(string organizationId, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Delete, $"organizations/{KeycloakAdminTransport.Escape(organizationId)}", cancellationToken: cancellationToken);
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<JsonElement>> GetMembersAsync(string organizationId, int first = 0, int maximum = 100, CancellationToken cancellationToken = default) => KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, $"organizations/{KeycloakAdminTransport.Escape(organizationId)}/members?first={first}&max={maximum}", cancellationToken: cancellationToken), static item => item.Clone());
    /// <inheritdoc />
    public async ValueTask AddMemberAsync(string organizationId, string userId, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Post, $"organizations/{KeycloakAdminTransport.Escape(organizationId)}/members", userId, cancellationToken);
    /// <inheritdoc />
    public async ValueTask RemoveMemberAsync(string organizationId, string userId, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Delete, $"organizations/{KeycloakAdminTransport.Escape(organizationId)}/members/{KeycloakAdminTransport.Escape(userId)}", cancellationToken: cancellationToken);
}
