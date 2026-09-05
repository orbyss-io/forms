namespace ProgramKit.Identity.Admin;

/// <summary>Administers portable realm roles, groups, and their user assignments.</summary>
public interface IIdentityAccessAdministration
{
    /// <summary>Gets all realm-wide roles available for portable assignment.</summary>
    ValueTask<IReadOnlyList<IdentityRole>> GetRolesAsync(CancellationToken cancellationToken = default);
    /// <summary>Creates a realm-wide role.</summary>
    ValueTask CreateRoleAsync(string name, string? description = null, CancellationToken cancellationToken = default);
    /// <summary>Deletes a realm-wide role by name.</summary>
    ValueTask DeleteRoleAsync(string roleName, CancellationToken cancellationToken = default);
    /// <summary>Adds a set of realm-wide roles to a user.</summary>
    ValueTask AddRolesToUserAsync(string userId, IReadOnlyCollection<IdentityRole> roles, CancellationToken cancellationToken = default);
    /// <summary>Removes a set of realm-wide roles from a user.</summary>
    ValueTask RemoveRolesFromUserAsync(string userId, IReadOnlyCollection<IdentityRole> roles, CancellationToken cancellationToken = default);
    /// <summary>Gets groups matching a provider-supported free-text search.</summary>
    ValueTask<IReadOnlyList<IdentityGroup>> GetGroupsAsync(string? search = null, CancellationToken cancellationToken = default);
    /// <summary>Creates a top-level group or a child beneath the supplied parent.</summary>
    ValueTask<string> CreateGroupAsync(string name, string? parentGroupId = null, CancellationToken cancellationToken = default);
    /// <summary>Deletes a group and its provider-defined descendants.</summary>
    ValueTask DeleteGroupAsync(string groupId, CancellationToken cancellationToken = default);
    /// <summary>Adds a user to a group.</summary>
    ValueTask AddUserToGroupAsync(string userId, string groupId, CancellationToken cancellationToken = default);
    /// <summary>Removes a user from a group.</summary>
    ValueTask RemoveUserFromGroupAsync(string userId, string groupId, CancellationToken cancellationToken = default);
}
