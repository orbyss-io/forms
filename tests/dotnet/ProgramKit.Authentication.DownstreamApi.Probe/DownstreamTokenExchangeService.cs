using ProgramKit.Authentication.TokenExchange;

/// <summary>Returns a delegated token while recording the exact exchange request.</summary>
internal sealed class DownstreamTokenExchangeService : ITokenExchangeService
{
    /// <summary>Gets the exchange-policy registration used by the downstream client.</summary>
    internal string? Registration { get; private set; }

    /// <summary>Gets the exact exchange request produced by the downstream client.</summary>
    internal TokenExchangeRequest? Request { get; private set; }

    /// <inheritdoc />
    public ValueTask<TokenExchangeResult> ExchangeAsync(
        string registration,
        TokenExchangeRequest request,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        Registration = registration;
        Request = request;
        return ValueTask.FromResult(
            new TokenExchangeResult(
                "delegated-access",
                "urn:ietf:params:oauth:token-type:access_token",
                "Bearer",
                DateTimeOffset.UtcNow.AddMinutes(1),
                request.Scopes));
    }
}
