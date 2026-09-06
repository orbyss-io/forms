namespace ProgramKit.Forms;

/// <summary>Describes bounded quarantined content without exposing a filesystem path.</summary>
public sealed record FormAttachmentContentWriteResult(string ContentKey, long Length, string Sha256, ReadOnlyMemory<byte> Prefix);
