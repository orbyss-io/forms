/// <summary>Provides a stable clock for proof freshness assertions.</summary>
internal sealed class DPoPProbeTimeProvider(DateTimeOffset now) : TimeProvider
{
    /// <inheritdoc />
    public override DateTimeOffset GetUtcNow() => now;
}
