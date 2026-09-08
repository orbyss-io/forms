namespace Orbyss.Forms;

/// <summary>Persists draft/submission aggregates with durable replay and audit history.</summary>
public interface IFormSubmissionStore
{
    /// <summary>Gets one aggregate by draft identifier.</summary>
    ValueTask<FormSubmissionAggregateSnapshot?> GetByDraftAsync(FormDraftId draftId, CancellationToken cancellationToken = default);

    /// <summary>Gets one aggregate by submission identifier.</summary>
    ValueTask<FormSubmissionAggregateSnapshot?> GetBySubmissionAsync(FormSubmissionId submissionId, CancellationToken cancellationToken = default);

    /// <summary>Enumerates bounded aggregate snapshots for query projection.</summary>
    IAsyncEnumerable<FormSubmissionAggregateSnapshot> FindAsync(CancellationToken cancellationToken = default);

    /// <summary>Finds an exact durable command replay and rejects reuse with different input.</summary>
    ValueTask<FormSubmissionPersistenceResult?> ReplayAsync(FormDraftId draftId, string idempotencyKey, string fingerprint, CancellationToken cancellationToken = default);

    /// <summary>Atomically persists one optimistic aggregate command and its replay/audit record.</summary>
    ValueTask<FormSubmissionPersistenceResult> PersistAsync(FormSubmissionPersistenceCommand command, CancellationToken cancellationToken = default);
}
