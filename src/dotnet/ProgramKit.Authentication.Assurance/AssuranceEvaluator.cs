using System.Globalization;
using System.Security.Claims;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.Assurance;

/// <summary>Evaluates exact ACR, AMR, and authentication-age requirements.</summary>
internal sealed class AssuranceEvaluator(
    IOptions<AssuranceOptions> options,
    TimeProvider timeProvider) : IAssuranceEvaluator
{
    /// <inheritdoc />
    public AssuranceEvaluation Evaluate(ClaimsPrincipal principal, string policy)
    {
        ArgumentNullException.ThrowIfNull(principal);
        ArgumentException.ThrowIfNullOrWhiteSpace(policy);
        if (!options.Value.Policies.TryGetValue(policy, out var requirement))
        {
            throw new InvalidOperationException($"Authentication assurance policy '{policy}' is not configured.");
        }

        var accepted = requirement.AcceptedAcrValues;
        var acr = principal.FindFirstValue("acr");
        if (accepted.Length > 0 && (acr is null || !accepted.Contains(acr, StringComparer.Ordinal)))
        {
            return Failure("assurance_acr_insufficient", requirement);
        }

        var methods = ReadAuthenticationMethods(principal);
        if (requirement.RequiredAmrValues.Any(required => !methods.Contains(required)))
        {
            return Failure("assurance_amr_insufficient", requirement);
        }

        if (requirement.MaximumAuthenticationAgeSeconds is int maximumAge)
        {
            var value = principal.FindFirstValue("auth_time");
            if (!long.TryParse(value, NumberStyles.None, CultureInfo.InvariantCulture, out var seconds))
            {
                return Failure("assurance_auth_time_missing", requirement);
            }
            DateTimeOffset authenticatedAt;
            try
            {
                authenticatedAt = DateTimeOffset.FromUnixTimeSeconds(seconds);
            }
            catch (ArgumentOutOfRangeException)
            {
                return Failure("assurance_auth_time_invalid", requirement);
            }
            var now = timeProvider.GetUtcNow();
            var skew = TimeSpan.FromSeconds(options.Value.ClockSkewSeconds);
            if (authenticatedAt > now.Add(skew)
                || authenticatedAt < now.Subtract(TimeSpan.FromSeconds(maximumAge)).Subtract(skew))
            {
                return Failure("assurance_authentication_stale", requirement);
            }
        }

        return new AssuranceEvaluation(true, null, accepted, requirement.MaximumAuthenticationAgeSeconds);
    }

    /// <summary>Reads repeated and JSON-array AMR claim representations.</summary>
    private static HashSet<string> ReadAuthenticationMethods(ClaimsPrincipal principal)
    {
        var methods = new HashSet<string>(StringComparer.Ordinal);
        foreach (var claim in principal.FindAll("amr"))
        {
            var value = claim.Value;
            if (value.StartsWith("[", StringComparison.Ordinal))
            {
                try
                {
                    var parsed = JsonSerializer.Deserialize<string[]>(value) ?? [];
                    foreach (var method in parsed.Where(item => !string.IsNullOrWhiteSpace(item)))
                    {
                        methods.Add(method);
                    }
                    continue;
                }
                catch (JsonException)
                {
                    // An invalid array representation cannot satisfy any required method.
                }
            }
            if (!string.IsNullOrWhiteSpace(value))
            {
                methods.Add(value);
            }
        }
        return methods;
    }

    /// <summary>Creates a stable failed evaluation while preserving step-up request metadata.</summary>
    private static AssuranceEvaluation Failure(string code, AssurancePolicy policy) =>
        new(false, code, policy.AcceptedAcrValues, policy.MaximumAuthenticationAgeSeconds);
}
