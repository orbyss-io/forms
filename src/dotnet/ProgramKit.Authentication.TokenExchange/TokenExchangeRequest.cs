namespace ProgramKit.Authentication.TokenExchange;

/// <summary>Defines one standards-based OAuth token-exchange request.</summary>
public sealed class TokenExchangeRequest
{
    /// <summary>Gets or sets the token representing the subject being delegated.</summary>
    public string SubjectToken { get; set; } = string.Empty;

    /// <summary>Gets or sets the URI identifying the subject-token type.</summary>
    public string SubjectTokenType { get; set; } = "urn:ietf:params:oauth:token-type:access_token";

    /// <summary>Gets or sets the requested output-token type URI.</summary>
    public string RequestedTokenType { get; set; } = "urn:ietf:params:oauth:token-type:access_token";

    /// <summary>Gets or sets an optional logical target audience.</summary>
    public string? Audience { get; set; }

    /// <summary>Gets or sets an optional absolute target resource URI.</summary>
    public string? Resource { get; set; }

    /// <summary>Gets or sets exact scopes used to downscope the exchanged token.</summary>
    public string[] Scopes { get; set; } = [];

    /// <summary>Gets or sets an optional token representing the acting party.</summary>
    public string? ActorToken { get; set; }

    /// <summary>Gets or sets the URI identifying the actor-token type.</summary>
    public string? ActorTokenType { get; set; }
}
