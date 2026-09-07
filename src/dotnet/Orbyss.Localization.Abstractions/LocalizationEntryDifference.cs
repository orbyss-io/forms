namespace Orbyss.Localization;

/// <summary>Describes one scoped message-and-locale change between immutable releases.</summary>
public sealed record LocalizationEntryDifference(
    LocalizationDifferenceKind Kind,
    string Key,
    LocalizationScope Scope,
    string LanguageTag,
    LocalizationReleaseEntry? Before,
    LocalizationReleaseEntry? After);
