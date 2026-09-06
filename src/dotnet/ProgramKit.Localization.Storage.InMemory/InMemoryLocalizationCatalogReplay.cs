namespace ProgramKit.Localization;

/// <summary>Binds one catalog idempotency key to its fingerprint and historical result.</summary>
internal sealed record InMemoryLocalizationCatalogReplay(string Fingerprint, LocalizationCatalogSnapshot Snapshot);
