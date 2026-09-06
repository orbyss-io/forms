namespace ProgramKit.Web.Discovery;

/// <summary>Describes one hashed file deliberately placed in the public projection.</summary>
internal sealed class PublicationResource
{
    /// <summary>Gets or sets the literal root-relative route.</summary>
    public required string Route { get; set; }

    /// <summary>Gets or sets the public-relative file location.</summary>
    public required string File { get; set; }

    /// <summary>Gets or sets the allowlisted media type.</summary>
    public required string ContentType { get; set; }

    /// <summary>Gets or sets the expected SHA-256.</summary>
    public required string Sha256 { get; set; }

    /// <summary>Gets or sets explicit indexing permission.</summary>
    public required bool Index { get; set; }

    /// <summary>Gets or sets the explicit public-only visibility marker.</summary>
    public required string Visibility { get; set; }
}
