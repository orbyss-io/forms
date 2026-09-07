namespace Orbyss.Localization;

/// <summary>Records one durable catalog mutation without embedding transport or provider identities.</summary>
public sealed record LocalizationCatalogAuditEntry(
    string Operation,
    string IdempotencyKey,
    LocalizationAuditActor Actor,
    DateTimeOffset RequestedAt,
    DateTimeOffset RecordedAt,
    string? CorrelationId,
    LocalizationConcurrencyToken? PreviousVersion,
    LocalizationConcurrencyToken Version);
