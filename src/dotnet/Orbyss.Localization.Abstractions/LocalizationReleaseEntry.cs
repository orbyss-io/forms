namespace Orbyss.Localization;

/// <summary>Contains one approved localized message in an immutable runtime release.</summary>
public sealed record LocalizationReleaseEntry(
    string Key,
    LocalizationScope Scope,
    string LanguageTag,
    TextDirection Direction,
    string Pattern,
    IReadOnlyList<LocalizationArgumentDefinition> Arguments);
