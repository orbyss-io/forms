using CShells; using CShells.Features; using Microsoft.Extensions.DependencyInjection; using Microsoft.Extensions.DependencyInjection.Extensions;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Composes explicitly high-privilege Keycloak realm operations.</summary>
[ShellFeature(name: "ProgramKit.Identity.Keycloak.Admin.RealmOperations", DisplayName = "Keycloak Realm Operations", Description = "Exposes Keycloak key metadata, events, and attack-detection maintenance.")]
public sealed class ProgramKitKeycloakRealmOperationsFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) { KeycloakAdminComposition.AddTransport(services, settings); services.TryAddSingleton<IKeycloakRealmOperations, KeycloakRealmOperations>(); }
}
