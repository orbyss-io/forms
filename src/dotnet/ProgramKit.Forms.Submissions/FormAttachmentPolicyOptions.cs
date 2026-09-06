namespace ProgramKit.Forms;

/// <summary>Configures a fail-closed attachment allowlist.</summary>
public sealed record FormAttachmentPolicyOptions(
    long MaximumBytes,
    IReadOnlyList<AllowedFormAttachmentType> AllowedTypes,
    int InspectionPrefixBytes = 512);
