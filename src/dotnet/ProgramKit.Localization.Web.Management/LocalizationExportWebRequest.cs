namespace ProgramKit.Localization.Web.Management;

/// <summary>Selects a bounded localization export format, scope, locales, and mapping metadata.</summary>
public sealed record LocalizationExportWebRequest(
    LocalizationImportFormat Format,
    LocalizationScope? Scope = null,
    IReadOnlyList<string>? LanguageTags = null,
    IReadOnlyDictionary<string, string>? Mapping = null,
    string? SuggestedBaseName = null);
