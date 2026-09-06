namespace ProgramKit.Forms;

/// <summary>Records one durable form-definition mutation without transport-specific data.</summary>
public sealed record FormDefinitionAuditEntry(
    string Operation,
    string IdempotencyKey,
    FormAuditActor Actor,
    DateTimeOffset RequestedAt,
    DateTimeOffset RecordedAt,
    string? CorrelationId,
    FormConcurrencyToken? PreviousVersion,
    FormConcurrencyToken Version);
