namespace ProgramKit.Authentication.Assurance;

/// <summary>Describes acceptable standard OIDC authentication-context evidence.</summary>
public sealed class AssurancePolicy
{
    /// <summary>Gets or sets exact acceptable Authentication Context Class Reference values.</summary>
    public string[] AcceptedAcrValues { get; set; } = [];

    /// <summary>Gets or sets Authentication Methods Reference values that must all be present.</summary>
    public string[] RequiredAmrValues { get; set; } = [];

    /// <summary>Gets or sets the maximum authentication age in seconds, or null for no freshness rule.</summary>
    public int? MaximumAuthenticationAgeSeconds { get; set; }
}
