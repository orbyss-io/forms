namespace Orbyss.Forms.Localization;

/// <summary>Returns a nonpersisted catalog merge and its stable integration diagnostics.</summary>
public sealed record FormLocalizationMergeResult(
    Orbyss.Localization.LocalizationCatalogDefinition Catalog,
    int AddedMessages,
    int RetainedMessages,
    IReadOnlyList<Orbyss.Localization.LocalizationDiagnostic> Diagnostics)
{
    /// <summary>Gets whether the merge is safe to persist.</summary>
    public bool Succeeded => Diagnostics.All(item => item.Severity != Orbyss.Localization.LocalizationDiagnosticSeverity.Error);
}
