namespace ProgramKit.Authentication.ClientCredentials;

/// <summary>Configures one OAuth client-credentials token source.</summary>
public sealed class ClientCredentialsRegistration
{
    /// <summary>Gets or sets the absolute OAuth token endpoint.</summary>
    public string TokenEndpoint { get; set; } = string.Empty;

    /// <summary>Gets or sets the OAuth client identifier.</summary>
    public string ClientId { get; set; } = string.Empty;

    /// <summary>Gets or sets the OAuth client secret supplied by a deployment secret provider.</summary>
    public string ClientSecret { get; set; } = string.Empty;

    /// <summary>Gets or sets `client_secret_basic` or `client_secret_post`.</summary>
    public string ClientAuthenticationMethod { get; set; } = "client_secret_basic";

    /// <summary>Gets or sets the exact scopes requested for the machine identity.</summary>
    public string[] Scopes { get; set; } = [];

    /// <summary>Gets or sets how early a cached token is refreshed, in seconds.</summary>
    public int RefreshBeforeExpirySeconds { get; set; } = 30;

    /// <summary>Gets or sets the token-endpoint request timeout, in seconds.</summary>
    public int TimeoutSeconds { get; set; } = 10;

    /// <summary>Gets or sets whether loopback HTTP is accepted during local development.</summary>
    public bool AllowHttpForLocalDevelopment { get; set; }
}
