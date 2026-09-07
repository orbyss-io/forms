namespace Orbyss.Localization;

/// <summary>Defines a BCP 47 locale, its direction, and an explicit optional fallback.</summary>
public sealed record LocaleDefinition(
    string LanguageTag,
    TextDirection Direction,
    string? FallbackLanguageTag = null,
    bool RequiredForPublication = false);
