namespace Orbyss.Localization;

/// <summary>Describes one locale-policy change between immutable releases.</summary>
public sealed record LocalizationLocaleDifference(
    LocalizationDifferenceKind Kind,
    string LanguageTag,
    LocaleDefinition? Before,
    LocaleDefinition? After);
