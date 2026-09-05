namespace ProgramKit.Identity.Admin;
/// <summary>An interactive enrollment or account-maintenance action.</summary>
public enum IdentityEnrollmentAction
{
    /// <summary>Verify ownership of the account email address.</summary>
    VerifyEmail,
    /// <summary>Choose or replace the password.</summary>
    UpdatePassword,
    /// <summary>Configure a time-based one-time-password authenticator.</summary>
    ConfigureTotp,
    /// <summary>Register a passkey or security key.</summary>
    RegisterPasskey,
    /// <summary>Complete required profile fields.</summary>
    UpdateProfile
}
