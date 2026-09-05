/// <summary>Provides a stable clock for exchange-expiry assertions.</summary>
internal sealed class ExchangeTimeProvider(DateTimeOffset now) : TimeProvider
{
    /// <inheritdoc />
    public override DateTimeOffset GetUtcNow() => now;
}
