namespace ProgramKit.Forms;

/// <summary>Supplies immutable attachment facts and quarantined content to a scanner.</summary>
public sealed record FormAttachmentScanRequest(
    FormAttachmentId AttachmentId,
    string FileName,
    string MediaType,
    long Length,
    string Sha256,
    Stream Content);
