namespace Orbyss.Localization;

/// <summary>Returns the exact catalog result originally bound to a durable command key.</summary>
public sealed record LocalizationCatalogPersistenceResult(
    LocalizationCatalogSnapshot Snapshot,
    bool WasReplay);
