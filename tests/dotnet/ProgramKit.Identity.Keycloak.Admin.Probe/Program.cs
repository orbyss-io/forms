using System.Text.Json;
using CShells;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using ProgramKit.Identity.Admin;
using ProgramKit.Identity.Keycloak.Admin;

if (Environment.GetEnvironmentVariable("PROGRAM_KIT_KEYCLOAK_ADMIN_URL") is { Length: > 0 })
{
    await RealKeycloakProbe.RunAsync();
    return;
}

var handler = new RecordingHandler();
using var client = new HttpClient(handler);
var settings = new ShellSettings(new ShellId("probe"), ["ProgramKit.Identity.Keycloak.Admin.Users"]);
settings.ConfigurationData[$"{KeycloakAdminOptions.SectionName}:ServerUrl"] = "http://localhost:8080";
settings.ConfigurationData[$"{KeycloakAdminOptions.SectionName}:Realm"] = "tenant realm";
settings.ConfigurationData[$"{KeycloakAdminOptions.SectionName}:AdminRealm"] = "service realm";
settings.ConfigurationData[$"{KeycloakAdminOptions.SectionName}:ClientId"] = "admin client";
settings.ConfigurationData[$"{KeycloakAdminOptions.SectionName}:ClientSecret"] = "admin/secret";
settings.ConfigurationData[$"{KeycloakAdminOptions.SectionName}:AllowHttpForLocalDevelopment"] = "true";
var services = new ServiceCollection();
services.AddSingleton<IHostEnvironment>(new ProbeEnvironment());
new ProgramKitKeycloakUsersAdminFeature(settings).ConfigureServices(services);
Require(services.All(descriptor => descriptor.ServiceType != typeof(IIdentityApplicationAdministration)), "enabling Users leaked the Applications subdomain");
new ProgramKitKeycloakApplicationsAdminFeature(settings).ConfigureServices(services);
new ProgramKitKeycloakScopesAdminFeature(settings).ConfigureServices(services);
new ProgramKitKeycloakAccessAdminFeature(settings).ConfigureServices(services);
new ProgramKitKeycloakEnrollmentAdminFeature(settings).ConfigureServices(services);
new ProgramKitKeycloakSessionsAdminFeature(settings).ConfigureServices(services);
new ProgramKitKeycloakAuthenticationFlowsAdminFeature(settings).ConfigureServices(services);
new ProgramKitKeycloakIdentityProvidersAdminFeature(settings).ConfigureServices(services);
new ProgramKitKeycloakOrganizationsAdminFeature(settings).ConfigureServices(services);
new ProgramKitKeycloakRealmOperationsFeature(settings).ConfigureServices(services);
services.RemoveAll<IHttpClientFactory>();
services.AddSingleton<IHttpClientFactory>(new ProbeHttpClientFactory(client));
await using var provider = services.BuildServiceProvider();

var users = provider.GetRequiredService<IIdentityUserAdministration>();
var found = await users.FindAsync("alice@example.test");
Require(found.Total == 1 && found.Items.Single().Username == "alice", "portable user projection failed");
Require(await users.CreateAsync(new("alice", "alice@example.test")) == "user-created", "user creation did not return its Location identifier");

var applications = provider.GetRequiredService<IIdentityApplicationAdministration>();
_ = await applications.CreateAsync(new("billing-api", ServiceAccountsEnabled: true));
Require(await applications.RotateSecretAsync("application-1") == "rotated-secret", "client secret rotation failed");

var scopes = provider.GetRequiredService<IIdentityScopeAdministration>();
Require((await scopes.GetAllAsync()).Single().Name == "billing.read", "portable scope projection failed");
_ = await scopes.AddClaimMappingAsync("scope-1", new("subscription", "subscription_tier", "subscription_tier"));

var access = provider.GetRequiredService<IIdentityAccessAdministration>();
var role = (await access.GetRolesAsync()).Single();
await access.AddRolesToUserAsync("user-1", [role]);

var enrollment = provider.GetRequiredService<IIdentityEnrollmentAdministration>();
await enrollment.SendActionsAsync("user-1", [IdentityEnrollmentAction.VerifyEmail, IdentityEnrollmentAction.RegisterPasskey]);
Require(handler.Requests.Any(request => request.Body?.Contains("webauthn-register-passwordless", StringComparison.Ordinal) == true), "portable passkey enrollment was not mapped");

await provider.GetRequiredService<IIdentitySessionAdministration>().LogoutUserAsync("user-1");
Require((await provider.GetRequiredService<IKeycloakRealmOperations>().GetKeyMetadataAsync()).GetProperty("active").GetProperty("RSA").GetString() == "kid-1", "Keycloak-only key metadata failed");
_ = await provider.GetRequiredService<IKeycloakAuthenticationFlowAdministration>().CreateFlowAsync("step-up");
_ = await provider.GetRequiredService<IKeycloakIdentityProviderAdministration>().GetAllAsync();
using var organization = JsonDocument.Parse("{\"name\":\"Acme\",\"alias\":\"acme\"}");
_ = await provider.GetRequiredService<IKeycloakOrganizationAdministration>().CreateAsync(organization.RootElement);

Require(handler.Requests.Count(request => request.PathAndQuery.EndsWith("/protocol/openid-connect/token", StringComparison.Ordinal)) == 1, "service-account token was not safely cached");
Require(handler.Requests.Any(request => request.PathAndQuery.Contains("/admin/realms/tenant%20realm/", StringComparison.Ordinal)), "target realm was not path encoded");
Console.WriteLine("Keycloak Admin REST features preserve subdomain opt-in, portable contracts, request security, and token caching.");

static void Require(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}
