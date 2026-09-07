namespace Orbyss.Localization;

/// <summary>Reports one proposed key-and-locale effect in an import preview.</summary>
public sealed record LocalizationImportChange(
    string Key,
    string LanguageTag,
    LocalizationScope Scope,
    LocalizationImportChangeKind Kind,
    string? ExistingPattern,
    string? ImportedPattern);
