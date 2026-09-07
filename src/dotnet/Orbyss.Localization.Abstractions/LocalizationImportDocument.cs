namespace Orbyss.Localization;

/// <summary>Contains provider-neutral entries and diagnostics produced by a format adapter.</summary>
public sealed record LocalizationImportDocument(
    IReadOnlyList<LocalizationImportEntry> Entries,
    IReadOnlyList<LocalizationDiagnostic> Diagnostics);
