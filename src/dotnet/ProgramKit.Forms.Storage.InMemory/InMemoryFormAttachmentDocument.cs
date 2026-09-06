namespace ProgramKit.Forms;

/// <summary>Contains current attachment metadata, audit, and exact replay history.</summary>
internal sealed record InMemoryFormAttachmentDocument(FormAttachmentSnapshot Snapshot, IReadOnlyList<FormOperationalAuditEntry> Audit, IReadOnlyList<InMemoryFormAttachmentReplay> Commands);
