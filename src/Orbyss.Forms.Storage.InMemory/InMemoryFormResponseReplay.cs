namespace Orbyss.Forms;

/// <summary>Binds one operational idempotency key to its historical result.</summary>
internal sealed record InMemoryFormResponseReplay(string IdempotencyKey, string Fingerprint, FormSubmissionAggregateSnapshot Snapshot);
