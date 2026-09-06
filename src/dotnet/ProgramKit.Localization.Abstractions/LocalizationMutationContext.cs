namespace ProgramKit.Localization;

/// <summary>Supplies replay, concurrency, attribution, and correlation data for a localization mutation.</summary>
public sealed record LocalizationMutationContext(
    string IdempotencyKey,
    LocalizationConcurrencyToken? ExpectedVersion,
    LocalizationAuditActor Actor,
    DateTimeOffset RequestedAt,
    string? CorrelationId = null);
