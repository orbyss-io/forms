/// <summary>Provides a stable clock for token-expiry assertions.</summary>
internal sealed class ProbeTimeProvider(DateTimeOffset now) : TimeProvider
{
    /// <inheritdoc />
    public override DateTimeOffset GetUtcNow() => now;
}
