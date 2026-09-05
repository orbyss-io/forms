namespace ProgramKit.Identity.Admin;

/// <summary>Administers portable OAuth/OIDC application lifecycle operations.</summary>
public interface IIdentityApplicationAdministration
{
    /// <summary>Finds a bounded page of registered applications by client identifier.</summary>
    ValueTask<IdentityPage<IdentityApplication>> FindAsync(string? clientId = null, int first = 0, int maximum = 100, CancellationToken cancellationToken = default);
    /// <summary>Gets one registered application, or returns null when absent.</summary>
    ValueTask<IdentityApplication?> GetAsync(string applicationId, CancellationToken cancellationToken = default);
    /// <summary>Creates an application and returns its stable provider identifier.</summary>
    ValueTask<string> CreateAsync(CreateIdentityApplication application, CancellationToken cancellationToken = default);
    /// <summary>Replaces the portable application configuration.</summary>
    ValueTask UpdateAsync(string applicationId, CreateIdentityApplication application, CancellationToken cancellationToken = default);
    /// <summary>Deletes an application registration.</summary>
    ValueTask DeleteAsync(string applicationId, CancellationToken cancellationToken = default);
    /// <summary>Rotates and returns the confidential application's new client secret.</summary>
    ValueTask<string> RotateSecretAsync(string applicationId, CancellationToken cancellationToken = default);
}
