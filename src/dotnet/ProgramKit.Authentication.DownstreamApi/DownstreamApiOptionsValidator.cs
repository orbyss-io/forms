using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.DownstreamApi;

/// <summary>Rejects ambiguous, unsafe, or incomplete downstream API registrations.</summary>
internal sealed class DownstreamApiOptionsValidator(IHostEnvironment environment)
    : IValidateOptions<DownstreamApiOptions>
{
    /// <inheritdoc />
    public ValidateOptionsResult Validate(string? name, DownstreamApiOptions options)
    {
        var failures = new List<string>();
        if (options.Registrations.Count == 0)
        {
            failures.Add($"{DownstreamApiOptions.SectionName}:Registrations must contain at least one registration.");
        }

        foreach (var (registrationName, registration) in options.Registrations)
        {
            var path = $"{DownstreamApiOptions.SectionName}:Registrations:{registrationName}";
            if (string.IsNullOrWhiteSpace(registrationName))
            {
                failures.Add($"{DownstreamApiOptions.SectionName}:Registrations contains an empty name.");
            }
            ValidateBaseAddress(registration, path, failures);
            if (registration.AccessMode is not ("ClientCredentials" or "TokenExchange"))
            {
                failures.Add($"{path}:AccessMode must be ClientCredentials or TokenExchange.");
            }
            if (string.IsNullOrWhiteSpace(registration.TokenRegistration))
            {
                failures.Add($"{path}:TokenRegistration is required.");
            }
            if (registration.Scopes.Any(scope => string.IsNullOrWhiteSpace(scope) || scope.Any(char.IsWhiteSpace)))
            {
                failures.Add($"{path}:Scopes must contain non-empty individual OAuth scope values.");
            }
            if (registration.AccessMode == "TokenExchange"
                && string.IsNullOrWhiteSpace(registration.Audience)
                && string.IsNullOrWhiteSpace(registration.Resource))
            {
                failures.Add($"{path} must downscope token exchange to an Audience or Resource.");
            }
            if (registration.Resource is not null
                && (!Uri.TryCreate(registration.Resource, UriKind.Absolute, out var resource)
                    || (resource.Scheme != Uri.UriSchemeHttps && resource.Scheme != Uri.UriSchemeHttp)))
            {
                failures.Add($"{path}:Resource must be an absolute HTTP or HTTPS URI.");
            }
        }
        return failures.Count == 0 ? ValidateOptionsResult.Success : ValidateOptionsResult.Fail(failures);
    }

    /// <summary>Validates the fixed downstream destination and development transport exception.</summary>
    private void ValidateBaseAddress(
        DownstreamApiRegistration registration,
        string path,
        ICollection<string> failures)
    {
        if (!Uri.TryCreate(registration.BaseAddress, UriKind.Absolute, out var address)
            || !string.IsNullOrEmpty(address.Query)
            || !string.IsNullOrEmpty(address.Fragment))
        {
            failures.Add($"{path}:BaseAddress must be an absolute URI without a query or fragment.");
            return;
        }
        var localHttpAllowed = environment.IsDevelopment()
            && registration.AllowHttpForLocalDevelopment
            && address.Scheme == Uri.UriSchemeHttp
            && address.IsLoopback;
        if (address.Scheme != Uri.UriSchemeHttps && !localHttpAllowed)
        {
            failures.Add($"{path}:BaseAddress must use HTTPS; local HTTP requires the explicit development override.");
        }
    }
}
