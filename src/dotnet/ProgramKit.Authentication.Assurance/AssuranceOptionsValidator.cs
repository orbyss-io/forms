using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.Assurance;

/// <summary>Rejects ambiguous or ineffective assurance policies.</summary>
internal sealed partial class AssuranceOptionsValidator : IValidateOptions<AssuranceOptions>
{
    /// <inheritdoc />
    public ValidateOptionsResult Validate(string? name, AssuranceOptions options)
    {
        var failures = new List<string>();
        if (options.Policies.Count == 0)
        {
            failures.Add($"{AssuranceOptions.SectionName}:Policies must contain at least one policy.");
        }
        if (options.ClockSkewSeconds is < 0 or > 120)
        {
            failures.Add($"{AssuranceOptions.SectionName}:ClockSkewSeconds must be between 0 and 120.");
        }
        foreach (var (policyName, policy) in options.Policies)
        {
            var path = $"{AssuranceOptions.SectionName}:Policies:{policyName}";
            if (!PolicyNamePattern().IsMatch(policyName))
            {
                failures.Add($"{path} has an invalid policy name.");
            }
            if (policy.AcceptedAcrValues.Length == 0
                && policy.RequiredAmrValues.Length == 0
                && policy.MaximumAuthenticationAgeSeconds is null)
            {
                failures.Add($"{path} must require ACR, AMR, or authentication freshness evidence.");
            }
            ValidateValues(policy.AcceptedAcrValues, $"{path}:AcceptedAcrValues", failures);
            ValidateValues(policy.RequiredAmrValues, $"{path}:RequiredAmrValues", failures);
            if (policy.MaximumAuthenticationAgeSeconds is < 0 or > 86400)
            {
                failures.Add($"{path}:MaximumAuthenticationAgeSeconds must be between 0 and 86400.");
            }
        }
        return failures.Count == 0 ? ValidateOptionsResult.Success : ValidateOptionsResult.Fail(failures);
    }

    /// <summary>Rejects empty and duplicate exact claim values.</summary>
    private static void ValidateValues(string[] values, string path, ICollection<string> failures)
    {
        if (values.Any(string.IsNullOrWhiteSpace)
            || values.Distinct(StringComparer.Ordinal).Count() != values.Length)
        {
            failures.Add($"{path} must contain unique non-empty values.");
        }
    }

    /// <summary>Matches stable lowercase policy identities.</summary>
    [GeneratedRegex("^[a-z][a-z0-9.-]{0,63}$", RegexOptions.CultureInvariant)]
    private static partial Regex PolicyNamePattern();
}
