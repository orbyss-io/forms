namespace Orbyss.Localization;

/// <summary>Binds separate in-memory retirement state to exact command replay evidence.</summary>
internal sealed record InMemoryLocalizationRetirement(string IdempotencyKey, string Fingerprint, LocalizationConcurrencyToken Version);
