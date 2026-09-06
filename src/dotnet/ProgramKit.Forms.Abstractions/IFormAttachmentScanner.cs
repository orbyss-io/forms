namespace ProgramKit.Forms;

/// <summary>Scans quarantined attachment content using a consumer-selected malware provider.</summary>
public interface IFormAttachmentScanner
{
    /// <summary>Returns a fail-closed verdict for one bounded quarantined stream.</summary>
    ValueTask<FormAttachmentScanResult> ScanAsync(FormAttachmentScanRequest request, CancellationToken cancellationToken = default);
}
