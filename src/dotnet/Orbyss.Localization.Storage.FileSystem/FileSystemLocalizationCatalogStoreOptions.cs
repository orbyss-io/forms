namespace Orbyss.Localization;

/// <summary>Configures bounded filesystem persistence for editable localization catalogs.</summary>
public sealed record FileSystemLocalizationCatalogStoreOptions(
    string DirectoryPath,
    int MaximumDocumentBytes = 16 * 1024 * 1024,
    int MaximumCatalogs = 10_000);
