namespace ProgramKit.Authentication.ClientCredentials;

/// <summary>Acquires cached tokens for named OAuth client-credentials registrations.</summary>
public interface IClientCredentialsTokenProvider
{
    /// <summary>Gets a usable access token for the named machine identity.</summary>
    /// <param name="registration">The exact configured registration name.</param>
    /// <param name="cancellationToken">Cancels token-endpoint I/O.</param>
    /// <returns>A usable access token with its local expiry bound.</returns>
    ValueTask<OAuthAccessToken> GetTokenAsync(
        string registration,
        CancellationToken cancellationToken = default);
}
