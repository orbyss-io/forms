using ProgramKit.Identity.Admin;

namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Implements portable session administration through Keycloak.</summary>
internal sealed class KeycloakSessionsAdministration(KeycloakAdminTransport transport) : IIdentitySessionAdministration
{
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<IdentitySession>> GetForUserAsync(string userId, CancellationToken cancellationToken = default) =>
        KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, $"users/{KeycloakAdminTransport.Escape(userId)}/sessions", cancellationToken: cancellationToken), KeycloakJson.Session);

    /// <inheritdoc />
    public async ValueTask LogoutUserAsync(string userId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Post, $"users/{KeycloakAdminTransport.Escape(userId)}/logout", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public async ValueTask LogoutAllAsync(CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Post, "logout-all", cancellationToken: cancellationToken);
}
