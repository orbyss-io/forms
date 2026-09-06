namespace ProgramKit.Forms;

/// <summary>Defines one internal durable aggregate replay result.</summary>
internal sealed record FormResponseCommand(string IdempotencyKey, string Fingerprint, FormSubmissionAggregateSnapshot Snapshot);
