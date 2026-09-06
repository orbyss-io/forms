namespace ProgramKit.Forms;

/// <summary>Reports persisted attachment metadata and replay status.</summary>
public sealed record FormAttachmentPersistenceResult(FormAttachmentSnapshot Snapshot, bool WasReplay);
