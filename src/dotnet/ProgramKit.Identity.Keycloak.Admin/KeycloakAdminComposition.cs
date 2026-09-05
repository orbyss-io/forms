using CShells;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Shares idempotent transport composition across opt-in subdomain features.</summary>
internal static class KeycloakAdminComposition
{
    /// <summary>Adds shared, idempotent Keycloak Admin REST transport services.</summary>
    public static void AddTransport(IServiceCollection services, ShellSettings settings)
    {
        services.Configure<KeycloakAdminOptions>(settings.GetConfigurationRoot().GetSection(KeycloakAdminOptions.SectionName));
        services.TryAddEnumerable(ServiceDescriptor.Singleton<IValidateOptions<KeycloakAdminOptions>, KeycloakAdminOptionsValidator>());
        services.AddHttpClient(KeycloakAdminTransport.HttpClientName);
        services.TryAddSingleton(TimeProvider.System);
        services.TryAddSingleton<KeycloakAdminTransport>();
    }
}
