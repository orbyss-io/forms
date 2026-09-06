namespace ProgramKit.Forms;

/// <summary>Stores untrusted bytes in quarantine and promotes only scanner-approved content.</summary>
public interface IFormAttachmentContentStore
{
    /// <summary>Writes a bounded stream to quarantine while computing its digest and inspection prefix.</summary>
    ValueTask<FormAttachmentContentWriteResult> WriteQuarantinedAsync(FormAttachmentId attachmentId, Stream content, long maximumBytes, int prefixBytes, CancellationToken cancellationToken = default);

    /// <summary>Opens quarantined content for scanning.</summary>
    ValueTask<Stream> OpenQuarantinedAsync(string contentKey, CancellationToken cancellationToken = default);

    /// <summary>Atomically promotes quarantined content and returns its new opaque provider key.</summary>
    ValueTask<string> PromoteAsync(string contentKey, CancellationToken cancellationToken = default);

    /// <summary>Opens promoted, verified content for an authorized caller.</summary>
    ValueTask<Stream> OpenAvailableAsync(string contentKey, CancellationToken cancellationToken = default);

    /// <summary>Removes quarantined or available bytes while metadata remains auditable.</summary>
    ValueTask DeleteAsync(string contentKey, CancellationToken cancellationToken = default);
}
