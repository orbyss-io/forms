using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.ClientCredentials;

/// <summary>Rejects incomplete or unsafe OAuth client-credentials registrations.</summary>
internal sealed class ClientCredentialsOptionsValidator(IHostEnvironment environment)
    : IValidateOptions<ClientCredentialsOptions>
{
    /// <inheritdoc />
    public ValidateOptionsResult Validate(string? name, ClientCredentialsOptions options)
    {
        var failures = new List<string>();
        if (options.Registrations.Count == 0)
        {
            failures.Add($"{ClientCredentialsOptions.SectionName}:Registrations must contain at least one registration.");
        }

        foreach (var (registrationName, registration) in options.Registrations)
        {
            var path = $"{ClientCredentialsOptions.SectionName}:Registrations:{registrationName}";
            if (string.IsNullOrWhiteSpace(registrationName))
            {
                failures.Add($"{ClientCredentialsOptions.SectionName}:Registrations contains an empty name.");
            }

            ValidateEndpoint(registration.TokenEndpoint, registration.AllowHttpForLocalDevelopment, path, failures);
            Require(registration.ClientId, $"{path}:ClientId", failures);
            Require(registration.ClientSecret, $"{path}:ClientSecret", failures);
            if (registration.ClientAuthenticationMethod is not ("client_secret_basic" or "client_secret_post"))
            {
                failures.Add($"{path}:ClientAuthenticationMethod must be client_secret_basic or client_secret_post.");
            }

            if (registration.Scopes.Any(scope => string.IsNullOrWhiteSpace(scope) || scope.Any(char.IsWhiteSpace)))
            {
                failures.Add($"{path}:Scopes must contain non-empty individual OAuth scope values.");
            }

            if (registration.RefreshBeforeExpirySeconds is < 0 or > 300)
            {
                failures.Add($"{path}:RefreshBeforeExpirySeconds must be between 0 and 300.");
            }

            if (registration.TimeoutSeconds is < 1 or > 60)
            {
                failures.Add($"{path}:TimeoutSeconds must be between 1 and 60.");
            }
        }

        return failures.Count == 0 ? ValidateOptionsResult.Success : ValidateOptionsResult.Fail(failures);
    }

    /// <summary>Validates transport and URI constraints for one token endpoint.</summary>
    private void ValidateEndpoint(
        string value,
        bool allowHttpForLocalDevelopment,
        string path,
        ICollection<string> failures)
    {
        if (!Uri.TryCreate(value, UriKind.Absolute, out var endpoint)
            || !string.IsNullOrEmpty(endpoint.Query)
            || !string.IsNullOrEmpty(endpoint.Fragment))
        {
            failures.Add($"{path}:TokenEndpoint must be an absolute URI without a query or fragment.");
            return;
        }

        var localHttpAllowed = environment.IsDevelopment()
            && allowHttpForLocalDevelopment
            && endpoint.Scheme == Uri.UriSchemeHttp
            && endpoint.IsLoopback;
        if (endpoint.Scheme != Uri.UriSchemeHttps && !localHttpAllowed)
        {
            failures.Add($"{path}:TokenEndpoint must use HTTPS; local HTTP requires the explicit development override.");
        }
    }

    /// <summary>Adds a path-specific validation failure for a missing value.</summary>
    private static void Require(string value, string path, ICollection<string> failures)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            failures.Add($"{path} is required.");
        }
    }
}
