namespace ProgramKit.Localization;

/// <summary>Selects catalog scope and locale content for a bounded interchange export.</summary>
public sealed record LocalizationExportRequest(
    LocalizationImportFormat Format,
    LocalizationCatalogDefinition Catalog,
    LocalizationScope? Scope = null,
    IReadOnlyList<string>? LanguageTags = null,
    IReadOnlyDictionary<string, string>? Mapping = null,
    string? SuggestedBaseName = null);
