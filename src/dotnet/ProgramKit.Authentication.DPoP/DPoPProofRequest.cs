namespace ProgramKit.Authentication.DPoP;

/// <summary>Describes one outbound RFC 9449 proof.</summary>
public sealed class DPoPProofRequest
{
    /// <summary>Gets or sets the outbound HTTP method.</summary>
    public required string Method { get; set; }

    /// <summary>Gets or sets the absolute target URI; query and fragment are excluded from `htu`.</summary>
    public required Uri TargetUri { get; set; }

    /// <summary>Gets or sets the access token whose hash is emitted as `ath`, when applicable.</summary>
    public string? AccessToken { get; set; }

    /// <summary>Gets or sets a server-provided `DPoP-Nonce` value.</summary>
    public string? Nonce { get; set; }

    /// <summary>Gets or sets an explicit proof identifier; a random identifier is used when omitted.</summary>
    public string? ProofIdentifier { get; set; }

    /// <summary>Gets or sets an explicit issuance time; the configured time provider is used when omitted.</summary>
    public DateTimeOffset? IssuedAt { get; set; }
}
