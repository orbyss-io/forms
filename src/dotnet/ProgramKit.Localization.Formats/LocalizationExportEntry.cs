namespace ProgramKit.Localization.Formats;

/// <summary>Represents one normalized value selected for deterministic serialization.</summary>
internal sealed record LocalizationExportEntry(
    string Key,
    string LanguageTag,
    LocalizationScope Scope,
    string SourcePattern,
    string Pattern,
    IReadOnlyList<LocalizationArgumentDefinition> Arguments,
    string? Description,
    string? Context,
    string? Provenance);
