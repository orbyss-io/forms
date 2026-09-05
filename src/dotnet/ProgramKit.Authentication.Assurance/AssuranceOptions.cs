namespace ProgramKit.Authentication.Assurance;

/// <summary>Defines named provider-neutral authentication-assurance policies.</summary>
public sealed class AssuranceOptions
{
    /// <summary>Gets the shell configuration section containing assurance policies.</summary>
    public const string SectionName = "ProgramKit:Authentication:Assurance";

    /// <summary>Gets policies keyed by an application-owned assurance name.</summary>
    public Dictionary<string, AssurancePolicy> Policies { get; } = new(StringComparer.Ordinal);

    /// <summary>Gets or sets the tolerated clock skew when validating authentication time.</summary>
    public int ClockSkewSeconds { get; set; } = 30;
}
