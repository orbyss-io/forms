using ProgramKit.Identity.Admin;

namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Implements portable credential and enrollment administration through Keycloak.</summary>
internal sealed class KeycloakEnrollmentAdministration(KeycloakAdminTransport transport) : IIdentityEnrollmentAdministration
{
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<IdentityCredential>> GetCredentialsAsync(string userId, CancellationToken cancellationToken = default) =>
        KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, $"users/{KeycloakAdminTransport.Escape(userId)}/credentials", cancellationToken: cancellationToken), KeycloakJson.Credential);

    /// <inheritdoc />
    public async ValueTask DeleteCredentialAsync(string userId, string credentialId, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Delete, $"users/{KeycloakAdminTransport.Escape(userId)}/credentials/{KeycloakAdminTransport.Escape(credentialId)}", cancellationToken: cancellationToken);

    /// <inheritdoc />
    public async ValueTask SetPasswordAsync(string userId, string password, bool temporary = true, CancellationToken cancellationToken = default) =>
        _ = await transport.SendAsync(HttpMethod.Put, $"users/{KeycloakAdminTransport.Escape(userId)}/reset-password", new { type = "password", value = password, temporary }, cancellationToken);

    /// <inheritdoc />
    public async ValueTask SendActionsAsync(string userId, IReadOnlyCollection<IdentityEnrollmentAction> actions, Uri? redirectUri = null, string? clientId = null, CancellationToken cancellationToken = default)
    {
        if (actions.Count == 0) throw new ArgumentException("At least one enrollment action is required.", nameof(actions));
        var query = new List<string>();
        if (redirectUri is not null) query.Add($"redirect_uri={KeycloakAdminTransport.Escape(redirectUri.AbsoluteUri)}");
        if (!string.IsNullOrWhiteSpace(clientId)) query.Add($"client_id={KeycloakAdminTransport.Escape(clientId)}");
        var path = $"users/{KeycloakAdminTransport.Escape(userId)}/execute-actions-email" + (query.Count == 0 ? string.Empty : $"?{string.Join('&', query)}");
        var requiredActions = actions.Select(Map).ToArray();
        _ = await transport.SendAsync(HttpMethod.Put, path, requiredActions, cancellationToken);
    }

    /// <summary>Maps a portable enrollment action to its Keycloak required-action alias.</summary>
    private static string Map(IdentityEnrollmentAction action) => action switch
    {
        IdentityEnrollmentAction.VerifyEmail => "VERIFY_EMAIL",
        IdentityEnrollmentAction.UpdatePassword => "UPDATE_PASSWORD",
        IdentityEnrollmentAction.ConfigureTotp => "CONFIGURE_TOTP",
        IdentityEnrollmentAction.RegisterPasskey => "webauthn-register-passwordless",
        IdentityEnrollmentAction.UpdateProfile => "UPDATE_PROFILE",
        _ => throw new ArgumentOutOfRangeException(nameof(action))
    };
}
