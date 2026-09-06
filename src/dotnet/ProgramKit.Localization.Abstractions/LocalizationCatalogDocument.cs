namespace ProgramKit.Localization;

/// <summary>Returns an editable catalog together with the opaque version required by its next mutation.</summary>
public sealed record LocalizationCatalogDocument(
    LocalizationCatalogDefinition Catalog,
    LocalizationConcurrencyToken Version);
