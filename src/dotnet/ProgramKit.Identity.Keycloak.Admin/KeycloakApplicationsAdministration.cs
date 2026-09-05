using ProgramKit.Identity.Admin;

namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Implements portable application administration through Keycloak.</summary>
internal sealed class KeycloakApplicationsAdministration(KeycloakAdminTransport transport) : IIdentityApplicationAdministration
{
    /// <inheritdoc />
    public async ValueTask<IdentityPage<IdentityApplication>> FindAsync(string? clientId = null, int first = 0, int maximum = 100, CancellationToken cancellationToken = default)
    {
        var query = new List<string> { $"first={first}", $"max={maximum}", "viewableOnly=true" };
        if (!string.IsNullOrWhiteSpace(clientId)) query.Add($"clientId={KeycloakAdminTransport.Escape(clientId)}");
        var value = await transport.SendAsync(HttpMethod.Get, $"clients?{string.Join('&', query)}", cancellationToken: cancellationToken);
        return new(KeycloakJson.Array(value, KeycloakJson.Application));
    }

    /// <inheritdoc />
    public async ValueTask<IdentityApplication?> GetAsync(string applicationId, CancellationToken cancellationToken = default)
    {
        var value = await transport.SendAsync(HttpMethod.Get, $"clients/{KeycloakAdminTransport.Escape(applicationId)}", cancellationToken: cancellationToken);
        return value is null ? null : KeycloakJson.Application(value.Value);
    }

    /// <inheritdoc />
    public ValueTask<string> CreateAsync(CreateIdentityApplication application, CancellationToken cancellationToken = default) =>
        transport.CreateAsync("clients", Representation(application), cancellationToken);

    /// <inheritdoc />
    public async ValueTask UpdateAsync(string applicationId, CreateIdentityApplication application, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Put, $"clients/{KeycloakAdminTransport.Escape(applicationId)}", Representation(application), cancellationToken);

    /// <inheritdoc />
    public async ValueTask DeleteAsync(string applicationId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Delete, $"clients/{KeycloakAdminTransport.Escape(applicationId)}", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public async ValueTask<string> RotateSecretAsync(string applicationId, CancellationToken cancellationToken = default)
    {
        var value = await transport.SendAsync(HttpMethod.Post, $"clients/{KeycloakAdminTransport.Escape(applicationId)}/client-secret", new { }, cancellationToken);
        var secret = value is null ? null : KeycloakJson.OptionalString(value.Value, "value");
        return !string.IsNullOrWhiteSpace(secret) ? secret : throw new InvalidDataException("Keycloak did not return the rotated client secret.");
    }

    /// <summary>Creates a Keycloak client representation from portable application fields.</summary>
    private static object Representation(CreateIdentityApplication value) => new
    {
        value.ClientId,
        value.Name,
        value.Enabled,
        value.PublicClient,
        redirectUris = value.RedirectUris ?? [],
        webOrigins = value.WebOrigins ?? [],
        value.ServiceAccountsEnabled,
        protocol = "openid-connect"
    };
}
