namespace ProgramKit.Authentication.DPoP;

/// <summary>Issues and atomically consumes opaque resource-server DPoP nonces.</summary>
/// <remarks>
/// Distributed deployments that require nonces should replace the default in-memory implementation
/// with a shared, atomic store.
/// </remarks>
public interface IDPoPNonceStore
{
    /// <summary>Creates a cryptographically random nonce valid until the supplied instant.</summary>
    string Issue(DateTimeOffset expiresAt);

    /// <summary>Returns true only when an unexpired nonce is consumed for the first time.</summary>
    bool TryConsume(string nonce);
}
