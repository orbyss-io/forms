/// <summary>Provides assertions shared by the probe's one-type-per-file collaborators.</summary>
internal static class ProbeAssertions
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
