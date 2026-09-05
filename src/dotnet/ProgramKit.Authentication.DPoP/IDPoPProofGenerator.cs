namespace ProgramKit.Authentication.DPoP;

/// <summary>Creates outbound RFC 9449 proofs using one stable client-held key.</summary>
public interface IDPoPProofGenerator
{
    /// <summary>Gets the RFC 7638 thumbprint used to bind access tokens to this key.</summary>
    string JwkThumbprint { get; }

    /// <summary>Creates a signed proof for one token or resource request.</summary>
    string CreateProof(DPoPProofRequest request);
}
