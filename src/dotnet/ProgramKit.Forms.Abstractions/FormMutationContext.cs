namespace ProgramKit.Forms;

/// <summary>Supplies replay, concurrency, attribution, and correlation data for a form mutation.</summary>
public sealed record FormMutationContext(
    string IdempotencyKey,
    FormConcurrencyToken? ExpectedVersion,
    FormAuditActor Actor,
    DateTimeOffset RequestedAt,
    string? CorrelationId = null);
