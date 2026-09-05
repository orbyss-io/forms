namespace ProgramKit.Authentication.DPoP;

/// <summary>Configures provider-neutral RFC 9449 resource-server validation.</summary>
public sealed class DPoPOptions
{
    /// <summary>Gets the shell configuration section containing DPoP settings.</summary>
    public const string SectionName = "ProgramKit:Authentication:DPoP";

    /// <summary>Gets or sets whether every authenticated request must use a DPoP-bound token.</summary>
    public bool Required { get; set; } = true;

    /// <summary>Gets or sets the externally visible origin used to validate `htu`.</summary>
    public string PublicOrigin { get; set; } = string.Empty;

    /// <summary>Gets or sets the maximum accepted age of a proof, in seconds.</summary>
    public int ProofMaxAgeSeconds { get; set; } = 60;

    /// <summary>Gets or sets the permitted proof-clock skew, in seconds.</summary>
    public int ClockSkewSeconds { get; set; } = 5;

    /// <summary>Gets or sets whether loopback HTTP is accepted during local development.</summary>
    public bool AllowHttpForLocalDevelopment { get; set; }

    /// <summary>Gets or sets whether each proof must carry a server-issued single-use nonce.</summary>
    public bool RequireNonce { get; set; }

    /// <summary>Gets or sets how long an issued nonce remains usable, in seconds.</summary>
    public int NonceLifetimeSeconds { get; set; } = 60;
}
