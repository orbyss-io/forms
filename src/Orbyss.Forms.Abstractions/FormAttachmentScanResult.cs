namespace Orbyss.Forms;

/// <summary>Represents a public-safe malware scan verdict.</summary>
public sealed record FormAttachmentScanResult(bool IsClean, string Code)
{
    /// <summary>Creates a scanner-approved verdict.</summary>
    public static FormAttachmentScanResult Clean() => new(true, "clean");

    /// <summary>Creates a scanner-rejected verdict with a stable public-safe code.</summary>
    public static FormAttachmentScanResult Reject(string code) => new(false, code);
}
