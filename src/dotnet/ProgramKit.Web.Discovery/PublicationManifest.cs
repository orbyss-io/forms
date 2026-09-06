namespace ProgramKit.Web.Discovery;

/// <summary>Describes the versioned, explicitly public build projection.</summary>
internal sealed class PublicationManifest
{
    /// <summary>Gets or sets the format version.</summary>
    public required string Version { get; set; }

    /// <summary>Gets or sets the complete literal route allowlist.</summary>
    public required List<PublicationResource> Resources { get; set; }
}
