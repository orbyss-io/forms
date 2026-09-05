/// <summary>Provides assertions shared by downstream probe collaborators.</summary>
internal static class DownstreamProbeAssertions
{
    /// <summary>Fails the probe when an invariant is false.</summary>
    internal static void Require(bool condition, string message)
    {
        if (!condition)
        {
            throw new InvalidOperationException(message);
        }
    }
}
