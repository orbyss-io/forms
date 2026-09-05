namespace ProgramKit.Authentication.Assurance;

/// <summary>Builds stable ASP.NET authorization policy names for authentication assurance.</summary>
public static class AssurancePolicyNames
{
    /// <summary>Gets the reserved prefix for assurance authorization policies.</summary>
    public const string Prefix = "assurance:";

    /// <summary>Builds the authorization-policy name for one configured assurance policy.</summary>
    public static string For(string policy)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(policy);
        return Prefix + policy;
    }
}
