using CShells; using CShells.Features; using Microsoft.Extensions.DependencyInjection; using Microsoft.Extensions.DependencyInjection.Extensions; using ProgramKit.Identity.Admin;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Composes portable credential and enrollment administration backed by Keycloak.</summary>
[ShellFeature(name: "ProgramKit.Identity.Keycloak.Admin.Enrollment", DisplayName = "Keycloak Enrollment Administration", Description = "Manages credentials and sends required-action enrollment messages.")]
public sealed class ProgramKitKeycloakEnrollmentAdminFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) { KeycloakAdminComposition.AddTransport(services, settings); services.TryAddSingleton<IIdentityEnrollmentAdministration, KeycloakEnrollmentAdministration>(); }
}
