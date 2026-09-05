using ProgramKit.Identity.Admin;

namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Implements portable role and group administration through Keycloak.</summary>
internal sealed class KeycloakAccessAdministration(KeycloakAdminTransport transport) : IIdentityAccessAdministration
{
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<IdentityRole>> GetRolesAsync(CancellationToken cancellationToken = default) =>
        KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, "roles", cancellationToken: cancellationToken), KeycloakJson.Role);

    /// <inheritdoc />
    public async ValueTask CreateRoleAsync(string name, string? description = null, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Post, "roles", new { name, description }, cancellationToken);

    /// <inheritdoc />
    public async ValueTask DeleteRoleAsync(string roleName, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Delete, $"roles/{KeycloakAdminTransport.Escape(roleName)}", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public async ValueTask AddRolesToUserAsync(string userId, IReadOnlyCollection<IdentityRole> roles, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Post, $"users/{KeycloakAdminTransport.Escape(userId)}/role-mappings/realm", RoleRepresentations(roles), cancellationToken);

    /// <inheritdoc />
    public async ValueTask RemoveRolesFromUserAsync(string userId, IReadOnlyCollection<IdentityRole> roles, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Delete, $"users/{KeycloakAdminTransport.Escape(userId)}/role-mappings/realm", RoleRepresentations(roles), cancellationToken);

    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<IdentityGroup>> GetGroupsAsync(string? search = null, CancellationToken cancellationToken = default)
    {
        var path = "groups" + (string.IsNullOrWhiteSpace(search) ? string.Empty : $"?search={KeycloakAdminTransport.Escape(search)}");
        return KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, path, cancellationToken: cancellationToken), KeycloakJson.Group);
    }

    /// <inheritdoc />
    public ValueTask<string> CreateGroupAsync(string name, string? parentGroupId = null, CancellationToken cancellationToken = default) =>
        transport.CreateAsync(parentGroupId is null ? "groups" : $"groups/{KeycloakAdminTransport.Escape(parentGroupId)}/children", new { name }, cancellationToken);

    /// <inheritdoc />
    public async ValueTask DeleteGroupAsync(string groupId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Delete, $"groups/{KeycloakAdminTransport.Escape(groupId)}", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public async ValueTask AddUserToGroupAsync(string userId, string groupId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Put, $"users/{KeycloakAdminTransport.Escape(userId)}/groups/{KeycloakAdminTransport.Escape(groupId)}", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public async ValueTask RemoveUserFromGroupAsync(string userId, string groupId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Delete, $"users/{KeycloakAdminTransport.Escape(userId)}/groups/{KeycloakAdminTransport.Escape(groupId)}", cancellationToken: cancellationToken);

    /// <summary>Projects portable roles into Keycloak role-mapping representations.</summary>
    private static object[] RoleRepresentations(IEnumerable<IdentityRole> roles) =>
        roles.Select(role => (object)new { role.Id, role.Name, role.Description, role.Composite }).ToArray();
}
