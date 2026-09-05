/// <summary>Provides assertions shared by token-exchange probe collaborators.</summary>
internal static class ExchangeProbeAssertions
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
