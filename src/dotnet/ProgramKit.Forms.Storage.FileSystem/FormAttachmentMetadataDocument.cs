namespace ProgramKit.Forms;

/// <summary>Defines the internal persisted attachment metadata envelope payload.</summary>
internal sealed record FormAttachmentMetadataDocument(FormAttachment Attachment, string? ContentKey, string Version, IReadOnlyList<FormOperationalAuditEntry> Audit, IReadOnlyList<FormAttachmentMetadataCommand> Commands);
