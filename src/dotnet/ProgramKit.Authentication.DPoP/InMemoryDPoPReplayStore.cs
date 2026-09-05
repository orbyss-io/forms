using System.Collections.Concurrent;

namespace ProgramKit.Authentication.DPoP;

/// <summary>Provides process-local, atomic DPoP replay protection for single-instance deployments.</summary>
public sealed class InMemoryDPoPReplayStore(TimeProvider timeProvider) : IDPoPReplayStore
{
    /// <summary>Tracks reserved proof identifiers until the end of their acceptance window.</summary>
    private readonly ConcurrentDictionary<string, long> expiries = new(StringComparer.Ordinal);

    /// <inheritdoc />
    public bool TryUse(string proofThumbprint, string proofIdentifier, DateTimeOffset expiresAt)
    {
        var now = timeProvider.GetUtcNow().ToUnixTimeSeconds();
        foreach (var replay in expiries)
        {
            if (replay.Value < now)
            {
                expiries.TryRemove(replay.Key, out _);
            }
        }

        return expiries.TryAdd(
            $"{proofThumbprint}:{proofIdentifier}", expiresAt.ToUnixTimeSeconds());
    }
}
