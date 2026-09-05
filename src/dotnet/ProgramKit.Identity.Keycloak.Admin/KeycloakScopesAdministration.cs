using ProgramKit.Identity.Admin;

namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Implements portable scope and claim-mapping administration through Keycloak.</summary>
internal sealed class KeycloakScopesAdministration(KeycloakAdminTransport transport) : IIdentityScopeAdministration
{
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<IdentityScope>> GetAllAsync(CancellationToken cancellationToken = default) =>
        KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, "client-scopes", cancellationToken: cancellationToken), KeycloakJson.Scope);

    /// <inheritdoc />
    public ValueTask<string> CreateAsync(string name, string? description = null, CancellationToken cancellationToken = default) =>
        transport.CreateAsync("client-scopes", new { name, description, protocol = "openid-connect" }, cancellationToken);

    /// <inheritdoc />
    public async ValueTask DeleteAsync(string scopeId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Delete, $"client-scopes/{KeycloakAdminTransport.Escape(scopeId)}", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public async ValueTask AddDefaultToApplicationAsync(string applicationId, string scopeId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Put, $"clients/{KeycloakAdminTransport.Escape(applicationId)}/default-client-scopes/{KeycloakAdminTransport.Escape(scopeId)}", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public async ValueTask AddOptionalToApplicationAsync(string applicationId, string scopeId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Put, $"clients/{KeycloakAdminTransport.Escape(applicationId)}/optional-client-scopes/{KeycloakAdminTransport.Escape(scopeId)}", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public async ValueTask RemoveFromApplicationAsync(string applicationId, string scopeId, bool optional, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Delete, $"clients/{KeycloakAdminTransport.Escape(applicationId)}/{(optional ? "optional" : "default")}-client-scopes/{KeycloakAdminTransport.Escape(scopeId)}", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public ValueTask<string> AddClaimMappingAsync(string scopeId, IdentityClaimMapping mapping, CancellationToken cancellationToken = default) =>
        transport.CreateAsync($"client-scopes/{KeycloakAdminTransport.Escape(scopeId)}/protocol-mappers/models", new
        {
            mapping.Name,
            protocol = "openid-connect",
            protocolMapper = "oidc-usermodel-attribute-mapper",
            config = new Dictionary<string, string>
            {
                ["user.attribute"] = mapping.UserAttribute,
                ["claim.name"] = mapping.TokenClaim,
                ["jsonType.label"] = mapping.ClaimType,
                ["access.token.claim"] = mapping.IncludeInAccessToken.ToString().ToLowerInvariant(),
                ["id.token.claim"] = mapping.IncludeInIdToken.ToString().ToLowerInvariant(),
                ["userinfo.token.claim"] = mapping.IncludeInUserInfo.ToString().ToLowerInvariant()
            }
        }, cancellationToken);
}
