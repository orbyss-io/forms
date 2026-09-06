namespace ProgramKit.Forms;

/// <summary>Persists editable form aggregates through atomic concurrency, idempotency, and audit semantics.</summary>
public interface IFormDefinitionStore
{
    /// <summary>Gets the current aggregate snapshot, or returns null when absent.</summary>
    ValueTask<FormDefinitionSnapshot?> GetAsync(FormId formId, CancellationToken cancellationToken = default);

    /// <summary>Enumerates current aggregate snapshots without exposing provider cursors.</summary>
    IAsyncEnumerable<FormDefinitionSnapshot> FindAsync(CancellationToken cancellationToken = default);

    /// <summary>Returns an exact durable command replay, or null when the key has not been observed.</summary>
    ValueTask<FormDefinitionPersistenceResult?> ReplayAsync(
        FormId formId,
        string idempotencyKey,
        string fingerprint,
        CancellationToken cancellationToken = default);

    /// <summary>Atomically writes or replays an exact form command.</summary>
    ValueTask<FormDefinitionPersistenceResult> WriteAsync(
        FormDefinitionPersistenceCommand command,
        CancellationToken cancellationToken = default);
}
