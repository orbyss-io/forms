using CShells; using CShells.Features; using Microsoft.Extensions.DependencyInjection; using Microsoft.Extensions.DependencyInjection.Extensions; using ProgramKit.Identity.Admin;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Composes portable session administration backed by Keycloak.</summary>
[ShellFeature(name: "ProgramKit.Identity.Keycloak.Admin.Sessions", DisplayName = "Keycloak Session Administration", Description = "Observes and revokes user sessions through portable identity contracts.")]
public sealed class ProgramKitKeycloakSessionsAdminFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) { KeycloakAdminComposition.AddTransport(services, settings); services.TryAddSingleton<IIdentitySessionAdministration, KeycloakSessionsAdministration>(); }
}
