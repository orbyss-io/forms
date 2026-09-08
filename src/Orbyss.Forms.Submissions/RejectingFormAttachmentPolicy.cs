namespace Orbyss.Forms;

/// <summary>Provides an explicit fail-closed attachment policy until a host selects an allowlist.</summary>
public sealed class RejectingFormAttachmentPolicy : IFormAttachmentPolicy
{
    /// <inheritdoc />
    public long MaximumBytes => 1;

    /// <inheritdoc />
    public int InspectionPrefixBytes => 16;

    /// <inheritdoc />
    public void ValidateDeclaration(string fileName, string mediaType) =>
        throw new FormAttachmentRejectedException("attachment-policy-not-configured");

    /// <inheritdoc />
    public void ValidateContent(string fileName, string mediaType, long length, ReadOnlySpan<byte> prefix) =>
        throw new FormAttachmentRejectedException("attachment-policy-not-configured");
}
