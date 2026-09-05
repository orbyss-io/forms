using CShells; using CShells.Features; using Microsoft.Extensions.DependencyInjection; using Microsoft.Extensions.DependencyInjection.Extensions;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Composes Keycloak-specific organization administration.</summary>
[ShellFeature(name: "ProgramKit.Identity.Keycloak.Admin.Organizations", DisplayName = "Keycloak Organization Administration", Description = "Manages Keycloak organizations and memberships.")]
public sealed class ProgramKitKeycloakOrganizationsAdminFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) { KeycloakAdminComposition.AddTransport(services, settings); services.TryAddSingleton<IKeycloakOrganizationAdministration, KeycloakOrganizationAdministration>(); }
}
