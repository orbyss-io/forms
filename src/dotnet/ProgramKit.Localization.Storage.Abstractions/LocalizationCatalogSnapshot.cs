namespace ProgramKit.Localization;

/// <summary>Returns the current catalog, opaque version, and append-only audit history.</summary>
public sealed record LocalizationCatalogSnapshot(
    LocalizationCatalogDefinition Catalog,
    LocalizationConcurrencyToken Version,
    IReadOnlyList<LocalizationCatalogAuditEntry> AuditTrail);
