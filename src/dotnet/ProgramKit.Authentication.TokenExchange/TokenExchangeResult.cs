namespace ProgramKit.Authentication.TokenExchange;

/// <summary>Represents a successful RFC 8693 token-exchange result.</summary>
/// <param name="AccessToken">The opaque issued token.</param>
/// <param name="IssuedTokenType">The URI identifying the issued token type.</param>
/// <param name="TokenType">The authorization scheme for an issued access token.</param>
/// <param name="ExpiresAt">The local absolute expiry when the server supplied a lifetime.</param>
/// <param name="Scopes">The exact scopes returned by the authorization server.</param>
public sealed record TokenExchangeResult(
    string AccessToken,
    string IssuedTokenType,
    string TokenType,
    DateTimeOffset? ExpiresAt,
    IReadOnlyList<string> Scopes);
