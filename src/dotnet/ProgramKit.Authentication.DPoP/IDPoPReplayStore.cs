namespace ProgramKit.Authentication.DPoP;

/// <summary>Atomically reserves accepted DPoP proof identifiers until their replay window expires.</summary>
/// <remarks>
/// Distributed deployments should replace the default in-memory implementation with a shared store
/// whose reservation operation is atomic across every resource-server instance.
/// </remarks>
public interface IDPoPReplayStore
{
    /// <summary>Returns true only when this proof identifier was reserved for the first time.</summary>
    bool TryUse(string proofThumbprint, string proofIdentifier, DateTimeOffset expiresAt);
}
