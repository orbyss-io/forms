namespace Orbyss.Localization;

/// <summary>Returns the catalog produced by applying an exact stored import preview.</summary>
public sealed record LocalizationImportApplicationResult(
    LocalizationCatalogDefinition Catalog,
    LocalizationImportPreview Preview);
