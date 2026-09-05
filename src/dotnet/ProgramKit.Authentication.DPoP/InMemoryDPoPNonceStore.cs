using System.Collections.Concurrent;
using System.Security.Cryptography;

namespace ProgramKit.Authentication.DPoP;

/// <summary>Provides process-local, single-use DPoP nonces for single-instance deployments.</summary>
public sealed class InMemoryDPoPNonceStore(TimeProvider timeProvider) : IDPoPNonceStore
{
    /// <summary>Tracks opaque nonce values until consumption or expiry.</summary>
    private readonly ConcurrentDictionary<string, long> expiries = new(StringComparer.Ordinal);

    /// <inheritdoc />
    public string Issue(DateTimeOffset expiresAt)
    {
        var nonce = Convert.ToBase64String(RandomNumberGenerator.GetBytes(32))
            .TrimEnd('=').Replace('+', '-').Replace('/', '_');
        expiries[nonce] = expiresAt.ToUnixTimeSeconds();
        return nonce;
    }

    /// <inheritdoc />
    public bool TryConsume(string nonce)
    {
        if (!expiries.TryRemove(nonce, out var expiry))
        {
            return false;
        }
        return expiry >= timeProvider.GetUtcNow().ToUnixTimeSeconds();
    }
}
