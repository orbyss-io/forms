using CShells;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using ProgramKit.Identity.Admin;
using ProgramKit.Identity.Keycloak.Admin;

/// <summary>Exercises portable administration contracts against a disposable real Keycloak realm.</summary>
internal static class RealKeycloakProbe
{
    /// <summary>Runs a create-use-delete lifecycle through only public CShell features.</summary>
    internal static async Task RunAsync()
    {
        await using var services = BuildProvider();
        var users = services.GetRequiredService<IIdentityUserAdministration>();
        var applications = services.GetRequiredService<IIdentityApplicationAdministration>();
        var scopes = services.GetRequiredService<IIdentityScopeAdministration>();
        var access = services.GetRequiredService<IIdentityAccessAdministration>();
        var enrollment = services.GetRequiredService<IIdentityEnrollmentAdministration>();
        var sessions = services.GetRequiredService<IIdentitySessionAdministration>();
        string? userId = null;
        string? applicationId = null;
        string? scopeId = null;
        string? groupId = null;
        const string roleName = "program-kit-admin-probe-role";
        try
        {
            userId = await users.CreateAsync(new("admin-probe-user", "admin-probe@example.test", "Admin", "Probe"));
            var found = await users.FindAsync("admin-probe-user");
            Require(found.Items.Any(user => user.Id == userId), "real user search did not find the created user");
            await users.UpdateAsync(userId, new("admin-probe-user", "admin-probe@example.test", "Updated", "Probe", true, true));
            Require((await users.GetAsync(userId))?.FirstName == "Updated", "real user update did not persist");

            await access.CreateRoleAsync(roleName, "Disposable Program Kit acceptance role");
            var role = (await access.GetRolesAsync()).Single(item => item.Name == roleName);
            await access.AddRolesToUserAsync(userId, [role]);
            await access.RemoveRolesFromUserAsync(userId, [role]);
            groupId = await access.CreateGroupAsync("program-kit-admin-probe-group");
            await access.AddUserToGroupAsync(userId, groupId);
            await access.RemoveUserFromGroupAsync(userId, groupId);

            applicationId = await applications.CreateAsync(new("program-kit-admin-created-client", "Admin-created client", ServiceAccountsEnabled: true));
            await applications.UpdateAsync(applicationId, new("program-kit-admin-created-client", "Updated client", ServiceAccountsEnabled: true));
            Require(!string.IsNullOrWhiteSpace(await applications.RotateSecretAsync(applicationId)), "real application secret rotation returned no secret");

            scopeId = await scopes.CreateAsync("program-kit-admin-created-scope", "Disposable acceptance scope");
            _ = await scopes.AddClaimMappingAsync(scopeId, new("tenant", "tenant_id", "tenant_id"));
            await scopes.AddOptionalToApplicationAsync(applicationId, scopeId);
            await scopes.RemoveFromApplicationAsync(applicationId, scopeId, optional: true);

            await enrollment.SetPasswordAsync(userId, "Disposable-Admin-Probe-Password-1!", temporary: true);
            Require((await enrollment.GetCredentialsAsync(userId)).Any(item => item.Type == "password"), "real password administration did not create a credential");
            Require((await sessions.GetForUserAsync(userId)).Count == 0, "new disposable user unexpectedly had sessions");
            Require((await services.GetRequiredService<IKeycloakRealmOperations>().GetKeyMetadataAsync()).ValueKind == System.Text.Json.JsonValueKind.Object, "real Keycloak key metadata was unavailable");
        }
        finally
        {
            if (scopeId is not null) await scopes.DeleteAsync(scopeId);
            if (applicationId is not null) await applications.DeleteAsync(applicationId);
            if (groupId is not null) await access.DeleteGroupAsync(groupId);
            try { await access.DeleteRoleAsync(roleName); } catch (HttpRequestException exception) when (exception.StatusCode == System.Net.HttpStatusCode.NotFound) { }
            if (userId is not null) await users.DeleteAsync(userId);
        }
        Console.WriteLine("Real Keycloak completed portable user, access, application, scope, enrollment, session, and realm-operation lifecycles.");
    }

    /// <summary>Composes all portable administration subdomains through their public shell features.</summary>
    private static ServiceProvider BuildProvider()
    {
        var settings = new ShellSettings(new ShellId("real-keycloak-probe"), []);
        var prefix = KeycloakAdminOptions.SectionName;
        settings.ConfigurationData[$"{prefix}:ServerUrl"] = RequiredEnvironment("PROGRAM_KIT_KEYCLOAK_ADMIN_URL");
        settings.ConfigurationData[$"{prefix}:Realm"] = "program-kit";
        settings.ConfigurationData[$"{prefix}:AdminRealm"] = "program-kit";
        settings.ConfigurationData[$"{prefix}:ClientId"] = "program-kit-admin-probe";
        settings.ConfigurationData[$"{prefix}:ClientSecret"] = RequiredEnvironment("PROGRAM_KIT_KEYCLOAK_ADMIN_SECRET");
        settings.ConfigurationData[$"{prefix}:AllowHttpForLocalDevelopment"] = "true";
        var collection = new ServiceCollection();
        collection.AddSingleton<IHostEnvironment>(new ProbeEnvironment());
        new ProgramKitKeycloakUsersAdminFeature(settings).ConfigureServices(collection);
        new ProgramKitKeycloakApplicationsAdminFeature(settings).ConfigureServices(collection);
        new ProgramKitKeycloakScopesAdminFeature(settings).ConfigureServices(collection);
        new ProgramKitKeycloakAccessAdminFeature(settings).ConfigureServices(collection);
        new ProgramKitKeycloakEnrollmentAdminFeature(settings).ConfigureServices(collection);
        new ProgramKitKeycloakSessionsAdminFeature(settings).ConfigureServices(collection);
        new ProgramKitKeycloakRealmOperationsFeature(settings).ConfigureServices(collection);
        return collection.BuildServiceProvider();
    }

    /// <summary>Reads one required disposable-fixture environment value.</summary>
    private static string RequiredEnvironment(string name) => Environment.GetEnvironmentVariable(name) ?? throw new InvalidOperationException($"{name} is required.");

    /// <summary>Fails the live probe when a lifecycle invariant is violated.</summary>
    private static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
}
