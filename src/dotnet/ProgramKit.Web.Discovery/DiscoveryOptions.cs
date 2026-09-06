namespace ProgramKit.Web.Discovery;

/// <summary>Configures the shell's generated public-content source, relative to the content root.</summary>
public sealed class DiscoveryOptions
{
    /// <summary>Identifies the shell configuration section.</summary>
    public const string SectionName = "ProgramKit:Web:Discovery";

    /// <summary>Gets or sets the generated directory containing publication.json and public/.</summary>
    public string OutputDirectory { get; set; } = "web/generated/program-kit";
}
