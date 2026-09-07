namespace Orbyss.Forms;

/// <summary>Uploads, scans, queries, opens, and removes draft-bound attachments.</summary>
public interface IFormAttachmentOperations
{
    /// <summary>Quarantines, verifies and scans one bounded upload before making it available.</summary>
    ValueTask<FormMutationResult<FormAttachment>> UploadAsync(FormAttachmentId attachmentId, FormDraftId draftId, string fileName, string mediaType, Stream content, FormMutationContext mutation, CancellationToken cancellationToken = default);

    /// <summary>Retries fail-closed scanning for content that remains quarantined.</summary>
    ValueTask<FormMutationResult<FormAttachment>> ScanAsync(FormAttachmentId attachmentId, FormMutationContext mutation, CancellationToken cancellationToken = default);

    /// <summary>Gets visible attachment metadata without exposing its storage locator.</summary>
    ValueTask<FormAttachmentDocument?> GetAsync(FormAttachmentId attachmentId, FormRequestContext request, CancellationToken cancellationToken = default);

    /// <summary>Finds visible attachment metadata for one draft.</summary>
    ValueTask<FormPage<FormAttachmentDocument>> FindAsync(FormDraftId draftId, FormRequestContext request, int first = 0, int maximum = 100, CancellationToken cancellationToken = default);

    /// <summary>Opens verified content for an available attachment visible to the request context.</summary>
    ValueTask<Stream> OpenReadAsync(FormAttachmentId attachmentId, FormRequestContext request, CancellationToken cancellationToken = default);

    /// <summary>Marks an attachment removed and makes its content unavailable.</summary>
    ValueTask<FormMutationResult<FormAttachment>> RemoveAsync(FormAttachmentId attachmentId, FormMutationContext mutation, CancellationToken cancellationToken = default);
}
