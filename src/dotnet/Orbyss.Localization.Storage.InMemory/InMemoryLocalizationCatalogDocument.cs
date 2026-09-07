namespace Orbyss.Localization;

/// <summary>Contains current catalog state and exact process-local replay records.</summary>
internal sealed record InMemoryLocalizationCatalogDocument(LocalizationCatalogSnapshot Snapshot, IReadOnlyDictionary<string, InMemoryLocalizationCatalogReplay> Commands);
