using System.Text.Json;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Implements Keycloak-specific external identity-provider administration.</summary>
internal sealed class KeycloakIdentityProviderAdministration(KeycloakAdminTransport transport) : IKeycloakIdentityProviderAdministration
{
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<JsonElement>> GetAllAsync(CancellationToken cancellationToken = default) => KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, "identity-provider/instances", cancellationToken: cancellationToken), static item => item.Clone());
    /// <inheritdoc />
    public async ValueTask<JsonElement?> GetAsync(string alias, CancellationToken cancellationToken = default) => await transport.SendAsync(HttpMethod.Get, $"identity-provider/instances/{KeycloakAdminTransport.Escape(alias)}", cancellationToken: cancellationToken);
    /// <inheritdoc />
    public ValueTask<string> CreateAsync(JsonElement representation, CancellationToken cancellationToken = default) => transport.CreateAsync("identity-provider/instances", representation, cancellationToken);
    /// <inheritdoc />
    public async ValueTask UpdateAsync(string alias, JsonElement representation, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Put, $"identity-provider/instances/{KeycloakAdminTransport.Escape(alias)}", representation, cancellationToken);
    /// <inheritdoc />
    public async ValueTask DeleteAsync(string alias, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Delete, $"identity-provider/instances/{KeycloakAdminTransport.Escape(alias)}", cancellationToken: cancellationToken);
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<JsonElement>> GetMappersAsync(string alias, CancellationToken cancellationToken = default) => KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, $"identity-provider/instances/{KeycloakAdminTransport.Escape(alias)}/mappers", cancellationToken: cancellationToken), static item => item.Clone());
    /// <inheritdoc />
    public async ValueTask CreateMapperAsync(string alias, JsonElement representation, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Post, $"identity-provider/instances/{KeycloakAdminTransport.Escape(alias)}/mappers", representation, cancellationToken);
    /// <inheritdoc />
    public async ValueTask UpdateMapperAsync(string alias, string mapperId, JsonElement representation, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Put, $"identity-provider/instances/{KeycloakAdminTransport.Escape(alias)}/mappers/{KeycloakAdminTransport.Escape(mapperId)}", representation, cancellationToken);
    /// <inheritdoc />
    public async ValueTask DeleteMapperAsync(string alias, string mapperId, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Delete, $"identity-provider/instances/{KeycloakAdminTransport.Escape(alias)}/mappers/{KeycloakAdminTransport.Escape(mapperId)}", cancellationToken: cancellationToken);
}
