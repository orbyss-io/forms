using ProgramKit.Forms;

/// <summary>Approves fixture content after proving the scanner received readable bytes.</summary>
internal sealed class CleanAttachmentScanner : IFormAttachmentScanner
{
    /// <inheritdoc />
    public async ValueTask<FormAttachmentScanResult> ScanAsync(FormAttachmentScanRequest request, CancellationToken cancellationToken = default)
    {
        var prefix = new byte[4];
        var read = await request.Content.ReadAsync(prefix, cancellationToken).ConfigureAwait(false);
        return read == 4 ? FormAttachmentScanResult.Clean() : FormAttachmentScanResult.Reject("fixture-too-short");
    }
}
