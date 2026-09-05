using Microsoft.Extensions.Options;
using Microsoft.Extensions.Hosting;

namespace ProgramKit.Authentication;

/// <summary>Rejects incomplete common authentication settings and ambiguous profile activation.</summary>
internal sealed class ProgramKitWebOptionsValidator(
    IHostEnvironment environment,
    IEnumerable<IProgramKitAuthenticationProfile> profiles) : IValidateOptions<ProgramKitWebOptions>
{
    /// <inheritdoc />
    public ValidateOptionsResult Validate(string? name, ProgramKitWebOptions options)
    {
        var failures = new List<string>();
        var selectedProfiles = profiles.Select(profile => profile.Name).Distinct(StringComparer.Ordinal).ToArray();
        if (selectedProfiles.Length != 1)
        {
            failures.Add(
                "Exactly one Program Kit authentication profile must be active in a shell; found: "
                + (selectedProfiles.Length == 0 ? "none" : string.Join(", ", selectedProfiles)));
        }

        Require(options.Authority, "ProgramKit:Web:Authority", failures);
        Require(options.ClientId, "ProgramKit:Web:ClientId", failures);
        Require(options.Audience, "ProgramKit:Web:Audience", failures);
        Require(options.RoleClaim, "ProgramKit:Web:RoleClaim", failures);
        Require(options.PermissionClaim, "ProgramKit:Web:PermissionClaim", failures);

        if (Uri.TryCreate(options.Authority, UriKind.Absolute, out var authority))
        {
            var localHttpAllowed = environment.IsDevelopment()
                && options.AllowHttpForLocalDevelopment
                && authority.Scheme == Uri.UriSchemeHttp
                && authority.IsLoopback;
            if (authority.Scheme != Uri.UriSchemeHttps && !localHttpAllowed)
            {
                failures.Add(
                    "ProgramKit:Web:Authority must use HTTPS; local HTTP requires the explicit development override.");
            }
        }
        else
        {
            failures.Add("ProgramKit:Web:Authority must be an absolute URI.");
        }

        if (!string.IsNullOrWhiteSpace(options.BackchannelAuthority))
        {
            if (Uri.TryCreate(options.BackchannelAuthority, UriKind.Absolute, out var backchannelAuthority))
            {
                var localHttpAllowed = environment.IsDevelopment()
                    && options.AllowHttpForLocalDevelopment
                    && backchannelAuthority.Scheme == Uri.UriSchemeHttp;
                if (backchannelAuthority.Scheme != Uri.UriSchemeHttps && !localHttpAllowed)
                {
                    failures.Add(
                        "ProgramKit:Web:BackchannelAuthority must use HTTPS; local HTTP requires the explicit development override.");
                }
                if (!string.IsNullOrEmpty(backchannelAuthority.Query)
                    || !string.IsNullOrEmpty(backchannelAuthority.Fragment))
                {
                    failures.Add("ProgramKit:Web:BackchannelAuthority must not contain a query or fragment.");
                }
            }
            else
            {
                failures.Add("ProgramKit:Web:BackchannelAuthority must be an absolute URI when configured.");
            }
        }

        if (options.Scopes.Length == 0 || !options.Scopes.Contains("openid", StringComparer.Ordinal))
        {
            failures.Add("ProgramKit:Web:Scopes must include openid.");
        }

        if (options.DiscoveryTimeoutSeconds is < 1 or > 30)
        {
            failures.Add("ProgramKit:Web:DiscoveryTimeoutSeconds must be between 1 and 30.");
        }

        if (options.SessionIdleMinutes < 1 || options.SessionAbsoluteMinutes < options.SessionIdleMinutes)
        {
            failures.Add(
                "ProgramKit:Web session lifetime must be positive and absolute lifetime must not be shorter than idle lifetime.");
        }

        ValidatePermissionMappings(options.RolePermissions, "RolePermissions", failures);
        ValidatePermissionMappings(options.ScopePermissions, "ScopePermissions", failures);
        return failures.Count == 0 ? ValidateOptionsResult.Success : ValidateOptionsResult.Fail(failures);
    }

    /// <summary>Adds a required-value failure for an empty setting.</summary>
    private static void Require(string value, string path, ICollection<string> failures)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            failures.Add($"{path} is required by the selected secure web profile.");
        }
    }

    /// <summary>Rejects empty provider keys and permission identities.</summary>
    private static void ValidatePermissionMappings(
        IReadOnlyDictionary<string, string[]> mappings,
        string name,
        ICollection<string> failures)
    {
        foreach (var (source, permissions) in mappings)
        {
            if (string.IsNullOrWhiteSpace(source)
                || permissions.Length == 0
                || permissions.Any(string.IsNullOrWhiteSpace))
            {
                failures.Add(
                    $"ProgramKit:Web:{name} must map a non-empty provider value to non-empty application permissions.");
            }
        }
    }
}
