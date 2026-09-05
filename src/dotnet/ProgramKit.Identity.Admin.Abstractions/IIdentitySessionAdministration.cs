namespace ProgramKit.Identity.Admin;

/// <summary>Observes and revokes portable user sessions.</summary>
public interface IIdentitySessionAdministration
{
    /// <summary>Gets the active login sessions for a user.</summary>
    ValueTask<IReadOnlyList<IdentitySession>> GetForUserAsync(string userId, CancellationToken cancellationToken = default);
    /// <summary>Revokes all active and offline sessions for one user.</summary>
    ValueTask LogoutUserAsync(string userId, CancellationToken cancellationToken = default);
    /// <summary>Revokes all active sessions for the configured identity domain.</summary>
    ValueTask LogoutAllAsync(CancellationToken cancellationToken = default);
}
