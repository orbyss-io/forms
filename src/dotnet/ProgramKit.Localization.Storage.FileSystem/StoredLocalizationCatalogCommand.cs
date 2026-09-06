namespace ProgramKit.Localization;

/// <summary>Persists the exact result originally associated with one idempotency key.</summary>
internal sealed record StoredLocalizationCatalogCommand(
    string Fingerprint,
    LocalizationCatalogDefinition Catalog,
    LocalizationConcurrencyToken Version,
    int AuditCount);
