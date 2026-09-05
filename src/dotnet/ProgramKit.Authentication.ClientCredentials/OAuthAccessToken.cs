namespace ProgramKit.Authentication.ClientCredentials;

/// <summary>Represents an OAuth access token and its bounded local expiry.</summary>
/// <param name="Value">The opaque access-token value.</param>
/// <param name="TokenType">The token type returned by the authorization server.</param>
/// <param name="ExpiresAt">The absolute time after which the token must not be used.</param>
public sealed record OAuthAccessToken(string Value, string TokenType, DateTimeOffset ExpiresAt);
