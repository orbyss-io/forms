using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Rejects incomplete credentials and unsafe Keycloak Admin REST endpoints.</summary>
internal sealed class KeycloakAdminOptionsValidator(IHostEnvironment environment)
    : IValidateOptions<KeycloakAdminOptions>
{
    /// <inheritdoc />
    public ValidateOptionsResult Validate(string? name, KeycloakAdminOptions options)
    {
        var failures = new List<string>();
        if (!Uri.TryCreate(options.ServerUrl, UriKind.Absolute, out var server)
            || !string.IsNullOrEmpty(server.Query)
            || !string.IsNullOrEmpty(server.Fragment))
        {
            failures.Add($"{KeycloakAdminOptions.SectionName}:ServerUrl must be an absolute URI without a query or fragment.");
        }
        else
        {
            var localHttp = environment.IsDevelopment()
                && options.AllowHttpForLocalDevelopment
                && server.Scheme == Uri.UriSchemeHttp
                && server.IsLoopback;
            if (server.Scheme != Uri.UriSchemeHttps && !localHttp)
            {
                failures.Add($"{KeycloakAdminOptions.SectionName}:ServerUrl must use HTTPS; local HTTP requires the explicit development override.");
            }
        }

        Require(options.Realm, nameof(options.Realm), failures);
        Require(options.AdminRealm, nameof(options.AdminRealm), failures);
        Require(options.ClientId, nameof(options.ClientId), failures);
        Require(options.ClientSecret, nameof(options.ClientSecret), failures);
        if (options.TimeoutSeconds is < 1 or > 120)
        {
            failures.Add($"{KeycloakAdminOptions.SectionName}:TimeoutSeconds must be between 1 and 120.");
        }
        if (options.RefreshBeforeExpirySeconds is < 0 or > 300)
        {
            failures.Add($"{KeycloakAdminOptions.SectionName}:RefreshBeforeExpirySeconds must be between 0 and 300.");
        }
        return failures.Count == 0 ? ValidateOptionsResult.Success : ValidateOptionsResult.Fail(failures);
    }

    /// <summary>Adds a path-specific validation failure for a missing setting.</summary>
    private static void Require(string value, string property, ICollection<string> failures)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            failures.Add($"{KeycloakAdminOptions.SectionName}:{property} is required.");
        }
    }
}
