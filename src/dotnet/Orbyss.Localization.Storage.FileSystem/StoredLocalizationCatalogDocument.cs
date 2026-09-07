namespace Orbyss.Localization;

/// <summary>Contains one current catalog plus its durable audit and command replay history.</summary>
internal sealed record StoredLocalizationCatalogDocument(
    LocalizationCatalogDefinition Catalog,
    LocalizationConcurrencyToken Version,
    IReadOnlyList<LocalizationCatalogAuditEntry> AuditTrail,
    IReadOnlyDictionary<string, StoredLocalizationCatalogCommand> Commands);
