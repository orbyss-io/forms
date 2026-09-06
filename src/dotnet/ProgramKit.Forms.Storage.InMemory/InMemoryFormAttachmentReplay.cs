namespace ProgramKit.Forms;

/// <summary>Binds one attachment idempotency key to its historical result.</summary>
internal sealed record InMemoryFormAttachmentReplay(string IdempotencyKey, string Fingerprint, FormAttachmentSnapshot Snapshot);
