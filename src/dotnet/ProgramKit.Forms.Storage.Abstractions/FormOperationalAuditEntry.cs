namespace ProgramKit.Forms;

/// <summary>Records server-observed audit evidence for one operational mutation.</summary>
public sealed record FormOperationalAuditEntry(string Operation, string IdempotencyKey, string Fingerprint, FormAuditActor Actor, DateTimeOffset RequestedAt, DateTimeOffset RecordedAt, string? CorrelationId);
