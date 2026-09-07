namespace Orbyss.Localization;

/// <summary>Stores the immutable audit and replay identity for one release retirement.</summary>
internal sealed record StoredLocalizationRetirement(
    string IdempotencyKey,
    string Fingerprint,
    LocalizationAuditActor Actor,
    DateTimeOffset RetiredAt,
    string? CorrelationId,
    LocalizationConcurrencyToken Version);
