namespace Orbyss.Forms;

/// <summary>Reports a stable public-safe attachment rejection without leaking scanner details.</summary>
public sealed class FormAttachmentRejectedException : InvalidOperationException
{
    /// <summary>Initializes a rejection with a stable machine-readable code.</summary>
    public FormAttachmentRejectedException(string code)
        : base($"The attachment was rejected by policy '{code}'.") => Code = code;

    /// <summary>Gets the stable rejection code.</summary>
    public string Code { get; }
}
