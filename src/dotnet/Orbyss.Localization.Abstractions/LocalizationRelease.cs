namespace Orbyss.Localization;

/// <summary>Represents an immutable, accepted localization release.</summary>
public sealed record LocalizationRelease(
    LocalizationReleaseId Id,
    LocalizationCatalogId CatalogId,
    LocalizationRevision Revision,
    string SourceLocale,
    IReadOnlyList<LocaleDefinition> Locales,
    IReadOnlyList<LocalizationReleaseEntry> Entries,
    string Sha256,
    DateTimeOffset PublishedAt,
    LocalizationAuditActor PublishedBy,
    bool Retired = false);
