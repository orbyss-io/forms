namespace ProgramKit.Identity.Admin;

/// <summary>Administers reusable scopes and portable user-attribute claim mappings.</summary>
public interface IIdentityScopeAdministration
{
    /// <summary>Gets all reusable scopes exposed by the provider.</summary>
    ValueTask<IReadOnlyList<IdentityScope>> GetAllAsync(CancellationToken cancellationToken = default);
    /// <summary>Creates a reusable scope and returns its stable provider identifier.</summary>
    ValueTask<string> CreateAsync(string name, string? description = null, CancellationToken cancellationToken = default);
    /// <summary>Deletes a reusable scope.</summary>
    ValueTask DeleteAsync(string scopeId, CancellationToken cancellationToken = default);
    /// <summary>Adds a scope to the application's default token request.</summary>
    ValueTask AddDefaultToApplicationAsync(string applicationId, string scopeId, CancellationToken cancellationToken = default);
    /// <summary>Adds a scope that an application can request explicitly.</summary>
    ValueTask AddOptionalToApplicationAsync(string applicationId, string scopeId, CancellationToken cancellationToken = default);
    /// <summary>Removes a default or optional scope assignment from an application.</summary>
    ValueTask RemoveFromApplicationAsync(string applicationId, string scopeId, bool optional, CancellationToken cancellationToken = default);
    /// <summary>Adds a portable user-attribute mapping to a reusable scope.</summary>
    ValueTask<string> AddClaimMappingAsync(string scopeId, IdentityClaimMapping mapping, CancellationToken cancellationToken = default);
}
