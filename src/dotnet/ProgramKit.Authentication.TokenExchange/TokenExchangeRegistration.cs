namespace ProgramKit.Authentication.TokenExchange;

/// <summary>Configures one OAuth RFC 8693 token-exchange client.</summary>
public sealed class TokenExchangeRegistration
{
    /// <summary>Gets or sets the absolute OAuth token endpoint.</summary>
    public string TokenEndpoint { get; set; } = string.Empty;

    /// <summary>Gets or sets the OAuth client identifier performing exchange.</summary>
    public string ClientId { get; set; } = string.Empty;

    /// <summary>Gets or sets the OAuth client secret supplied by a deployment secret provider.</summary>
    public string ClientSecret { get; set; } = string.Empty;

    /// <summary>Gets or sets `client_secret_basic` or `client_secret_post`.</summary>
    public string ClientAuthenticationMethod { get; set; } = "client_secret_basic";

    /// <summary>Gets or sets the token-endpoint request timeout, in seconds.</summary>
    public int TimeoutSeconds { get; set; } = 10;

    /// <summary>Gets or sets whether loopback HTTP is accepted during local development.</summary>
    public bool AllowHttpForLocalDevelopment { get; set; }
}
