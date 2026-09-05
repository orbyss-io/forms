using ProgramKit.Identity.Admin;

namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Implements portable user administration through Keycloak.</summary>
internal sealed class KeycloakUsersAdministration(KeycloakAdminTransport transport) : IIdentityUserAdministration
{
    /// <inheritdoc />
    public async ValueTask<IdentityPage<IdentityUser>> FindAsync(string? search = null, int first = 0, int maximum = 100, CancellationToken cancellationToken = default)
    {
        var query = new List<string> { $"first={first}", $"max={maximum}" };
        if (!string.IsNullOrWhiteSpace(search)) query.Add($"search={KeycloakAdminTransport.Escape(search)}");
        var value = await transport.SendAsync(HttpMethod.Get, $"users?{string.Join('&', query)}", cancellationToken: cancellationToken);
        var count = await transport.SendAsync(HttpMethod.Get, "users/count", cancellationToken: cancellationToken);
        return new(KeycloakJson.Array(value, KeycloakJson.User), count is { ValueKind: System.Text.Json.JsonValueKind.Number } number ? number.GetInt32() : null);
    }

    /// <inheritdoc />
    public async ValueTask<IdentityUser?> GetAsync(string userId, CancellationToken cancellationToken = default)
    {
        var value = await transport.SendAsync(HttpMethod.Get, $"users/{KeycloakAdminTransport.Escape(userId)}", cancellationToken: cancellationToken);
        return value is null ? null : KeycloakJson.User(value.Value);
    }

    /// <inheritdoc />
    public ValueTask<string> CreateAsync(CreateIdentityUser user, CancellationToken cancellationToken = default) =>
        transport.CreateAsync("users", new { user.Username, user.Email, user.FirstName, user.LastName, user.Enabled, user.EmailVerified, attributes = user.Attributes }, cancellationToken);

    /// <inheritdoc />
    public async ValueTask UpdateAsync(string userId, UpdateIdentityUser user, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Put, $"users/{KeycloakAdminTransport.Escape(userId)}", new { user.Username, user.Email, user.FirstName, user.LastName, user.Enabled, user.EmailVerified, attributes = user.Attributes }, cancellationToken);

    /// <inheritdoc />
    public async ValueTask DeleteAsync(string userId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Delete, $"users/{KeycloakAdminTransport.Escape(userId)}", cancellationToken: cancellationToken);
}
