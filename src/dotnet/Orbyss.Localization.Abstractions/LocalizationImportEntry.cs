namespace Orbyss.Localization;

/// <summary>Represents one locale value proposed by a parsed interchange document.</summary>
public sealed record LocalizationImportEntry(
    string Key,
    string LanguageTag,
    LocalizationScope Scope,
    string Pattern,
    string? SourcePattern = null,
    IReadOnlyList<LocalizationArgumentDefinition>? Arguments = null,
    string? Description = null,
    string? Context = null,
    string? Provenance = null);
