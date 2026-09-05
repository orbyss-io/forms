using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.DPoP;

/// <summary>Rejects unsafe or ambiguous DPoP resource-server settings.</summary>
internal sealed class DPoPOptionsValidator(IHostEnvironment environment) : IValidateOptions<DPoPOptions>
{
    /// <inheritdoc />
    public ValidateOptionsResult Validate(string? name, DPoPOptions options)
    {
        var failures = new List<string>();
        if (!Uri.TryCreate(options.PublicOrigin, UriKind.Absolute, out var origin)
            || origin.AbsolutePath != "/"
            || !string.IsNullOrEmpty(origin.Query)
            || !string.IsNullOrEmpty(origin.Fragment))
        {
            failures.Add("ProgramKit:Authentication:DPoP:PublicOrigin must be an exact absolute origin.");
        }
        else
        {
            var localHttpAllowed = environment.IsDevelopment()
                && options.AllowHttpForLocalDevelopment
                && origin.Scheme == Uri.UriSchemeHttp
                && origin.IsLoopback;
            if (origin.Scheme != Uri.UriSchemeHttps && !localHttpAllowed)
            {
                failures.Add(
                    "ProgramKit:Authentication:DPoP:PublicOrigin must use HTTPS; local HTTP requires the explicit development override.");
            }
        }

        if (options.ProofMaxAgeSeconds is < 10 or > 300)
        {
            failures.Add("ProgramKit:Authentication:DPoP:ProofMaxAgeSeconds must be between 10 and 300.");
        }
        if (options.ClockSkewSeconds is < 0 or > 30)
        {
            failures.Add("ProgramKit:Authentication:DPoP:ClockSkewSeconds must be between 0 and 30.");
        }
        if (options.NonceLifetimeSeconds is < 10 or > 300)
        {
            failures.Add("ProgramKit:Authentication:DPoP:NonceLifetimeSeconds must be between 10 and 300.");
        }
        return failures.Count == 0 ? ValidateOptionsResult.Success : ValidateOptionsResult.Fail(failures);
    }
}
