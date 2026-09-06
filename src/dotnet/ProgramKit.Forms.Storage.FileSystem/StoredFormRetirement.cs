namespace ProgramKit.Forms;

/// <summary>Stores immutable audit and replay identity for one form-release retirement.</summary>
internal sealed record StoredFormRetirement(
    string IdempotencyKey,
    string Fingerprint,
    FormAuditActor Actor,
    DateTimeOffset RetiredAt,
    string? CorrelationId,
    FormConcurrencyToken Version);
