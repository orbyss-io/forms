using CShells; using CShells.Features; using Microsoft.Extensions.DependencyInjection; using Microsoft.Extensions.DependencyInjection.Extensions; using ProgramKit.Identity.Admin;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Composes portable application administration backed by Keycloak.</summary>
[ShellFeature(name: "ProgramKit.Identity.Keycloak.Admin.Applications", DisplayName = "Keycloak Application Administration", Description = "Manages OAuth/OIDC clients through portable identity contracts.")]
public sealed class ProgramKitKeycloakApplicationsAdminFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) { KeycloakAdminComposition.AddTransport(services, settings); services.TryAddSingleton<IIdentityApplicationAdministration, KeycloakApplicationsAdministration>(); }
}
