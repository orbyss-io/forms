namespace ProgramKit.Identity.Admin;

/// <summary>Administers portable user-account lifecycle operations.</summary>
public interface IIdentityUserAdministration
{
    /// <summary>Finds a bounded page of users by a provider-supported free-text search.</summary>
    ValueTask<IdentityPage<IdentityUser>> FindAsync(string? search = null, int first = 0, int maximum = 100, CancellationToken cancellationToken = default);
    /// <summary>Gets one user by its stable provider identifier, or returns null when absent.</summary>
    ValueTask<IdentityUser?> GetAsync(string userId, CancellationToken cancellationToken = default);
    /// <summary>Creates a user and returns its stable provider identifier.</summary>
    ValueTask<string> CreateAsync(CreateIdentityUser user, CancellationToken cancellationToken = default);
    /// <summary>Replaces the portable mutable fields of an existing user.</summary>
    ValueTask UpdateAsync(string userId, UpdateIdentityUser user, CancellationToken cancellationToken = default);
    /// <summary>Deletes an existing user account.</summary>
    ValueTask DeleteAsync(string userId, CancellationToken cancellationToken = default);
}
