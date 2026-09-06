namespace ProgramKit.Forms;

/// <summary>Contains one deterministic compiled form artifact and its content hash.</summary>
public sealed record FormArtifact(string MediaType, string Content, string Sha256);
