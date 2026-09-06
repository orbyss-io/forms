namespace ProgramKit.Forms.Localization;

/// <summary>Returns a nonpersisted catalog merge and its stable integration diagnostics.</summary>
public sealed record FormLocalizationMergeResult(
    ProgramKit.Localization.LocalizationCatalogDefinition Catalog,
    int AddedMessages,
    int RetainedMessages,
    IReadOnlyList<ProgramKit.Localization.LocalizationDiagnostic> Diagnostics)
{
    /// <summary>Gets whether the merge is safe to persist.</summary>
    public bool Succeeded => Diagnostics.All(item => item.Severity != ProgramKit.Localization.LocalizationDiagnosticSeverity.Error);
}
