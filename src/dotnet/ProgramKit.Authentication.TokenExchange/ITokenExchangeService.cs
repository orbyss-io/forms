namespace ProgramKit.Authentication.TokenExchange;

/// <summary>Exchanges subject and optional actor tokens through named RFC 8693 policies.</summary>
public interface ITokenExchangeService
{
    /// <summary>Performs one bounded, non-cached token exchange.</summary>
    /// <param name="registration">The exact configured exchange-policy name.</param>
    /// <param name="request">The standards-based exchange request.</param>
    /// <param name="cancellationToken">Cancels token-endpoint I/O.</param>
    /// <returns>The issued token and its server-provided metadata.</returns>
    ValueTask<TokenExchangeResult> ExchangeAsync(
        string registration,
        TokenExchangeRequest request,
        CancellationToken cancellationToken = default);
}
