namespace ProgramKit.Forms;

/// <summary>Defines one internal durable attachment replay result.</summary>
internal sealed record FormAttachmentMetadataCommand(string IdempotencyKey, string Fingerprint, FormAttachmentSnapshot Snapshot);
