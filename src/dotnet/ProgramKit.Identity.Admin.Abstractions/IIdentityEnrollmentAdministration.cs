namespace ProgramKit.Identity.Admin;

/// <summary>Administers credentials and starts user-facing enrollment actions.</summary>
public interface IIdentityEnrollmentAdministration
{
    /// <summary>Gets the credentials currently enrolled for a user.</summary>
    ValueTask<IReadOnlyList<IdentityCredential>> GetCredentialsAsync(string userId, CancellationToken cancellationToken = default);
    /// <summary>Deletes one enrolled credential from a user.</summary>
    ValueTask DeleteCredentialAsync(string userId, string credentialId, CancellationToken cancellationToken = default);
    /// <summary>Sets a user password, temporary by default so the user must replace it.</summary>
    ValueTask SetPasswordAsync(string userId, string password, bool temporary = true, CancellationToken cancellationToken = default);
    /// <summary>Sends a user-facing link that starts the selected enrollment actions.</summary>
    ValueTask SendActionsAsync(string userId, IReadOnlyCollection<IdentityEnrollmentAction> actions, Uri? redirectUri = null, string? clientId = null, CancellationToken cancellationToken = default);
}
