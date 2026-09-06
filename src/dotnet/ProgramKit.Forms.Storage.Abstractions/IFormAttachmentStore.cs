namespace ProgramKit.Forms;

/// <summary>Persists attachment metadata separately from untrusted binary content.</summary>
public interface IFormAttachmentStore
{
    /// <summary>Gets attachment metadata by identifier.</summary>
    ValueTask<FormAttachmentSnapshot?> GetAsync(FormAttachmentId attachmentId, CancellationToken cancellationToken = default);

    /// <summary>Enumerates attachment metadata for one draft.</summary>
    IAsyncEnumerable<FormAttachmentSnapshot> FindByDraftAsync(FormDraftId draftId, CancellationToken cancellationToken = default);

    /// <summary>Finds an exact durable attachment-command replay.</summary>
    ValueTask<FormAttachmentPersistenceResult?> ReplayAsync(FormAttachmentId attachmentId, string idempotencyKey, string fingerprint, CancellationToken cancellationToken = default);

    /// <summary>Persists one optimistic attachment metadata command and its audit record.</summary>
    ValueTask<FormAttachmentPersistenceResult> PersistAsync(FormAttachmentPersistenceCommand command, CancellationToken cancellationToken = default);
}
