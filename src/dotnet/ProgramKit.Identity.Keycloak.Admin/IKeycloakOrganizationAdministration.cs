using System.Text.Json;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Keycloak-specific organization administration.</summary>
public interface IKeycloakOrganizationAdministration
{
    /// <summary>Finds a bounded page of organization representations.</summary>
    ValueTask<IReadOnlyList<JsonElement>> FindAsync(string? search = null, int first = 0, int maximum = 100, CancellationToken cancellationToken = default);
    /// <summary>Gets one organization representation, or returns null when absent.</summary>
    ValueTask<JsonElement?> GetAsync(string organizationId, CancellationToken cancellationToken = default);
    /// <summary>Creates an organization and returns its identifier.</summary>
    ValueTask<string> CreateAsync(JsonElement representation, CancellationToken cancellationToken = default);
    /// <summary>Updates an organization representation.</summary>
    ValueTask UpdateAsync(string organizationId, JsonElement representation, CancellationToken cancellationToken = default);
    /// <summary>Deletes an organization.</summary>
    ValueTask DeleteAsync(string organizationId, CancellationToken cancellationToken = default);
    /// <summary>Gets a bounded page of organization members.</summary>
    ValueTask<IReadOnlyList<JsonElement>> GetMembersAsync(string organizationId, int first = 0, int maximum = 100, CancellationToken cancellationToken = default);
    /// <summary>Adds an existing user as an organization member.</summary>
    ValueTask AddMemberAsync(string organizationId, string userId, CancellationToken cancellationToken = default);
    /// <summary>Removes a user from an organization without implicitly deleting an unmanaged user.</summary>
    ValueTask RemoveMemberAsync(string organizationId, string userId, CancellationToken cancellationToken = default);
}
