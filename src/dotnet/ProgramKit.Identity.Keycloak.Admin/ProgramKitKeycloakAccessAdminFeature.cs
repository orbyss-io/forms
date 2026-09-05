using CShells; using CShells.Features; using Microsoft.Extensions.DependencyInjection; using Microsoft.Extensions.DependencyInjection.Extensions; using ProgramKit.Identity.Admin;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Composes portable role and group administration backed by Keycloak.</summary>
[ShellFeature(name: "ProgramKit.Identity.Keycloak.Admin.Access", DisplayName = "Keycloak Access Administration", Description = "Manages roles, groups, and user assignments through portable identity contracts.")]
public sealed class ProgramKitKeycloakAccessAdminFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) { KeycloakAdminComposition.AddTransport(services, settings); services.TryAddSingleton<IIdentityAccessAdministration, KeycloakAccessAdministration>(); }
}
