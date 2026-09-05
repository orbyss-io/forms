/// <summary>Provides a stable clock for assurance-freshness tests.</summary>
internal sealed class AssuranceProbeTimeProvider(DateTimeOffset now) : TimeProvider
{
    /// <inheritdoc />
    public override DateTimeOffset GetUtcNow() => now;
}
