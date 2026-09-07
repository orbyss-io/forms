namespace Orbyss.Localization;

/// <summary>Represents an editable application-wide localization catalog revision.</summary>
public sealed record LocalizationCatalogDefinition(
    LocalizationCatalogId Id,
    LocalizationRevision Revision,
    string Name,
    string SourceLocale,
    LocalizationLifecycleState State,
    IReadOnlyList<LocaleDefinition> Locales,
    IReadOnlyList<LocalizationMessageDefinition> Messages,
    IReadOnlyDictionary<string, string>? Metadata = null);
