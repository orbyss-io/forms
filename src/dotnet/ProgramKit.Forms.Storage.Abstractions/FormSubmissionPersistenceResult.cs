namespace ProgramKit.Forms;

/// <summary>Reports persisted aggregate state and whether it came from durable replay.</summary>
public sealed record FormSubmissionPersistenceResult(FormSubmissionAggregateSnapshot Snapshot, bool WasReplay);
