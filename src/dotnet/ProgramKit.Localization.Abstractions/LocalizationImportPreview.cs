namespace ProgramKit.Localization;

/// <summary>Represents a hash-bound import proposal that can be reviewed before mutation.</summary>
public sealed record LocalizationImportPreview(
    string PreviewId,
    string ContentSha256,
    LocalizationRevision BasedOnRevision,
    LocalizationMergePolicy MergePolicy,
    IReadOnlyList<LocalizationImportChange> Changes,
    IReadOnlyList<LocalizationDiagnostic> Diagnostics);
