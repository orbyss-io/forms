namespace ProgramKit.Authentication.ClientCredentials;

/// <summary>Defines named provider-neutral OAuth client-credentials registrations.</summary>
public sealed class ClientCredentialsOptions
{
    /// <summary>Gets the configuration section containing client-credentials registrations.</summary>
    public const string SectionName = "ProgramKit:Authentication:ClientCredentials";

    /// <summary>Gets registrations keyed by the application-owned token-source name.</summary>
    public Dictionary<string, ClientCredentialsRegistration> Registrations { get; } =
        new(StringComparer.Ordinal);
}
