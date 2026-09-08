using System.Runtime.CompilerServices;

namespace Orbyss.Forms;

/// <summary>Stores draft/submission aggregates with atomic process-local replay and audit semantics.</summary>
public sealed class InMemoryFormSubmissionStore : IFormSubmissionStore
{
    /// <summary>Serializes aggregate access.</summary>
    private readonly object gate = new();
    /// <summary>Holds draft/submission state and replay history by draft identifier.</summary>
    private readonly Dictionary<string, InMemoryFormResponseDocument> documents = new(StringComparer.Ordinal);
    /// <summary>Bounds aggregate and command counts.</summary>
    private readonly InMemoryFormStorageOptions options;
    /// <summary>Supplies server-observed audit timestamps.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Initializes an empty bounded response store.</summary>
    public InMemoryFormSubmissionStore(InMemoryFormStorageOptions? options = null, TimeProvider? timeProvider = null)
    {
        this.options = options ?? new InMemoryFormStorageOptions(); InMemoryFormStorageCodec.Validate(this.options); this.timeProvider = timeProvider ?? TimeProvider.System;
    }

    /// <inheritdoc />
    public ValueTask<FormSubmissionAggregateSnapshot?> GetByDraftAsync(FormDraftId draftId, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(draftId.Value);
        lock (gate) return ValueTask.FromResult(documents.TryGetValue(draftId.Value, out var document) ? InMemoryFormStorageCodec.Clone<FormSubmissionAggregateSnapshot>(document.Snapshot) : null);
    }

    /// <inheritdoc />
    public ValueTask<FormSubmissionAggregateSnapshot?> GetBySubmissionAsync(FormSubmissionId submissionId, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(submissionId.Value);
        lock (gate)
        {
            var snapshot = documents.Values.Select(item => item.Snapshot).SingleOrDefault(item => item.Submission?.Id == submissionId);
            return ValueTask.FromResult(snapshot is null ? null : InMemoryFormStorageCodec.Clone<FormSubmissionAggregateSnapshot>(snapshot));
        }
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<FormSubmissionAggregateSnapshot> FindAsync([EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        FormSubmissionAggregateSnapshot[] found;
        lock (gate) found = documents.Values.Select(item => InMemoryFormStorageCodec.Clone(item.Snapshot)).OrderBy(item => item.Draft.CreatedAt).ThenBy(item => item.Draft.Id.Value, StringComparer.Ordinal).ToArray();
        foreach (var snapshot in found) { cancellationToken.ThrowIfCancellationRequested(); yield return snapshot; await Task.Yield(); }
    }

    /// <inheritdoc />
    public ValueTask<FormSubmissionPersistenceResult?> ReplayAsync(FormDraftId draftId, string idempotencyKey, string fingerprint, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(draftId.Value); ArgumentException.ThrowIfNullOrWhiteSpace(idempotencyKey); ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint);
        lock (gate)
        {
            var replay = documents.TryGetValue(draftId.Value, out var document) ? document.Commands.SingleOrDefault(item => string.Equals(item.IdempotencyKey, idempotencyKey, StringComparison.Ordinal)) : null;
            if (replay is null) return ValueTask.FromResult<FormSubmissionPersistenceResult?>(null);
            if (!string.Equals(replay.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form operation idempotency key was already used with different input.");
            return ValueTask.FromResult<FormSubmissionPersistenceResult?>(new(InMemoryFormStorageCodec.Clone(replay.Snapshot), true));
        }
    }

    /// <inheritdoc />
    public ValueTask<FormSubmissionPersistenceResult> PersistAsync(FormSubmissionPersistenceCommand command, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateCommand(command);
        lock (gate)
        {
            documents.TryGetValue(command.Draft.Id.Value, out var current);
            var replay = current?.Commands.SingleOrDefault(item => string.Equals(item.IdempotencyKey, command.Mutation.IdempotencyKey, StringComparison.Ordinal));
            if (replay is not null)
            {
                if (!string.Equals(replay.Fingerprint, command.Fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form operation idempotency key was already used with different input.");
                return ValueTask.FromResult(new FormSubmissionPersistenceResult(InMemoryFormStorageCodec.Clone(replay.Snapshot), true));
            }
            if (command.RequireAbsent)
            {
                if (current is not null) throw new InvalidOperationException("The form draft already exists.");
                if (documents.Count >= options.MaximumDocuments) throw new InvalidOperationException("The in-memory form response limit was reached.");
            }
            else
            {
                if (current is null) throw new InvalidOperationException("The form draft does not exist.");
                if (!string.Equals(command.Mutation.ExpectedVersion?.Value, current.Snapshot.Version.Value, StringComparison.Ordinal)) throw new InvalidOperationException("The form response changed since it was read.");
            }
            var draft = InMemoryFormStorageCodec.Clone(command.Draft);
            var submission = command.Submission is null ? null : InMemoryFormStorageCodec.Clone(command.Submission);
            var audit = (current?.Snapshot.Audit ?? []).Append(new FormOperationalAuditEntry(command.Operation, command.Mutation.IdempotencyKey, command.Fingerprint, command.Mutation.Actor, command.Mutation.RequestedAt, timeProvider.GetUtcNow(), command.Mutation.CorrelationId)).ToArray();
            var version = new FormConcurrencyToken(InMemoryFormStorageCodec.Hash(new { draft, submission, audit }));
            var snapshot = new FormSubmissionAggregateSnapshot(draft, submission, version, audit);
            var commands = (current?.Commands ?? []).Append(new InMemoryFormResponseReplay(command.Mutation.IdempotencyKey, command.Fingerprint, snapshot)).ToArray();
            if (commands.Length > options.MaximumCommandsPerDocument) throw new InvalidOperationException("The in-memory form response command history limit was reached.");
            var document = new InMemoryFormResponseDocument(snapshot, commands);
            InMemoryFormStorageCodec.EnsureSize(document, options.MaximumDocumentBytes);
            documents[draft.Id.Value] = document;
            return ValueTask.FromResult(new FormSubmissionPersistenceResult(InMemoryFormStorageCodec.Clone(snapshot), false));
        }
    }

    /// <summary>Rejects missing domain identifiers.</summary>
    private static void ValidateId(string value) => ArgumentException.ThrowIfNullOrWhiteSpace(value);
    /// <summary>Rejects incomplete or cross-aggregate persistence commands.</summary>
    private static void ValidateCommand(FormSubmissionPersistenceCommand command)
    {
        ArgumentNullException.ThrowIfNull(command); ArgumentNullException.ThrowIfNull(command.Draft); ArgumentNullException.ThrowIfNull(command.Mutation); ArgumentException.ThrowIfNullOrWhiteSpace(command.Operation); ArgumentException.ThrowIfNullOrWhiteSpace(command.Fingerprint); ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.IdempotencyKey);
        if (command.Submission is not null && command.Submission.DraftId != command.Draft.Id) throw new ArgumentException("A submission must belong to the persisted draft.", nameof(command));
    }
}
