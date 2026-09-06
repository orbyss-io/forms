namespace ProgramKit.Forms;

/// <summary>Provides an explicit fail-closed scanner default for consumers that have not selected a malware scanner.</summary>
public sealed class RejectingFormAttachmentScanner : IFormAttachmentScanner
{
    /// <inheritdoc />
    public ValueTask<FormAttachmentScanResult> ScanAsync(FormAttachmentScanRequest request, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        cancellationToken.ThrowIfCancellationRequested();
        return ValueTask.FromResult(FormAttachmentScanResult.Reject("scanner-not-configured"));
    }
}
