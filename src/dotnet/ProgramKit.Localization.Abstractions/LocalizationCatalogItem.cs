namespace ProgramKit.Localization;

/// <summary>Provides a bounded localization catalog projection for management search results.</summary>
public sealed record LocalizationCatalogItem(
    LocalizationCatalogId Id,
    string Name,
    string SourceLocale,
    LocalizationRevision Revision,
    LocalizationLifecycleState State,
    LocalizationConcurrencyToken Version);
