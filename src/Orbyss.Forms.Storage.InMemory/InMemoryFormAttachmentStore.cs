using System.Runtime.CompilerServices;

namespace Orbyss.Forms;

/// <summary>Stores attachment metadata independently from binary content in process memory.</summary>
public sealed class InMemoryFormAttachmentStore : IFormAttachmentStore
{
    /// <summary>Serializes attachment metadata access.</summary>
    private readonly object gate = new();
    /// <summary>Holds metadata, audit, and replay history by attachment identifier.</summary>
    private readonly Dictionary<string, InMemoryFormAttachmentDocument> documents = new(StringComparer.Ordinal);
    /// <summary>Bounds metadata and command counts.</summary>
    private readonly InMemoryFormStorageOptions options;
    /// <summary>Supplies server-observed audit timestamps.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Initializes an empty bounded metadata store.</summary>
    public InMemoryFormAttachmentStore(InMemoryFormStorageOptions? options = null, TimeProvider? timeProvider = null)
    {
        this.options = options ?? new InMemoryFormStorageOptions(); InMemoryFormStorageCodec.Validate(this.options); this.timeProvider = timeProvider ?? TimeProvider.System;
    }

    /// <inheritdoc />
    public ValueTask<FormAttachmentSnapshot?> GetAsync(FormAttachmentId attachmentId, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(attachmentId.Value);
        lock (gate) return ValueTask.FromResult(documents.TryGetValue(attachmentId.Value, out var document) ? InMemoryFormStorageCodec.Clone<FormAttachmentSnapshot>(document.Snapshot) : null);
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<FormAttachmentSnapshot> FindByDraftAsync(FormDraftId draftId, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ValidateId(draftId.Value); FormAttachmentSnapshot[] found;
        lock (gate) found = documents.Values.Select(item => item.Snapshot).Where(item => item.Attachment.DraftId == draftId).OrderBy(item => item.Attachment.CreatedAt).ThenBy(item => item.Attachment.Id.Value, StringComparer.Ordinal).Select(item => InMemoryFormStorageCodec.Clone(item)).ToArray();
        foreach (var snapshot in found) { cancellationToken.ThrowIfCancellationRequested(); yield return snapshot; await Task.Yield(); }
    }

    /// <inheritdoc />
    public ValueTask<FormAttachmentPersistenceResult?> ReplayAsync(FormAttachmentId attachmentId, string idempotencyKey, string fingerprint, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(attachmentId.Value); ArgumentException.ThrowIfNullOrWhiteSpace(idempotencyKey); ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint);
        lock (gate)
        {
            var replay = documents.TryGetValue(attachmentId.Value, out var document) ? document.Commands.SingleOrDefault(item => string.Equals(item.IdempotencyKey, idempotencyKey, StringComparison.Ordinal)) : null;
            if (replay is null) return ValueTask.FromResult<FormAttachmentPersistenceResult?>(null);
            if (!string.Equals(replay.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The attachment idempotency key was already used with different input.");
            return ValueTask.FromResult<FormAttachmentPersistenceResult?>(new(InMemoryFormStorageCodec.Clone(replay.Snapshot), true));
        }
    }

    /// <inheritdoc />
    public ValueTask<FormAttachmentPersistenceResult> PersistAsync(FormAttachmentPersistenceCommand command, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateCommand(command);
        lock (gate)
        {
            documents.TryGetValue(command.Attachment.Id.Value, out var current);
            var replay = current?.Commands.SingleOrDefault(item => string.Equals(item.IdempotencyKey, command.Mutation.IdempotencyKey, StringComparison.Ordinal));
            if (replay is not null)
            {
                if (!string.Equals(replay.Fingerprint, command.Fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The attachment idempotency key was already used with different input.");
                return ValueTask.FromResult(new FormAttachmentPersistenceResult(InMemoryFormStorageCodec.Clone(replay.Snapshot), true));
            }
            if (command.RequireAbsent)
            {
                if (current is not null) throw new InvalidOperationException("The attachment identifier already exists.");
                if (documents.Count >= options.MaximumDocuments) throw new InvalidOperationException("The in-memory attachment metadata limit was reached.");
            }
            else
            {
                if (current is null) throw new InvalidOperationException("The attachment does not exist.");
                if (!string.Equals(command.Mutation.ExpectedVersion?.Value, current.Snapshot.Version.Value, StringComparison.Ordinal)) throw new InvalidOperationException("The attachment changed since it was read.");
            }
            var attachment = InMemoryFormStorageCodec.Clone(command.Attachment);
            var audit = (current?.Audit ?? []).Append(new FormOperationalAuditEntry(command.Operation, command.Mutation.IdempotencyKey, command.Fingerprint, command.Mutation.Actor, command.Mutation.RequestedAt, timeProvider.GetUtcNow(), command.Mutation.CorrelationId)).ToArray();
            var version = new FormConcurrencyToken(InMemoryFormStorageCodec.Hash(new { attachment, command.ContentKey, audit }));
            var snapshot = new FormAttachmentSnapshot(attachment, command.ContentKey, version);
            var commands = (current?.Commands ?? []).Append(new InMemoryFormAttachmentReplay(command.Mutation.IdempotencyKey, command.Fingerprint, snapshot)).ToArray();
            if (commands.Length > options.MaximumCommandsPerDocument) throw new InvalidOperationException("The in-memory attachment command history limit was reached.");
            var document = new InMemoryFormAttachmentDocument(snapshot, audit, commands);
            InMemoryFormStorageCodec.EnsureSize(document, options.MaximumDocumentBytes);
            documents[attachment.Id.Value] = document;
            return ValueTask.FromResult(new FormAttachmentPersistenceResult(InMemoryFormStorageCodec.Clone(snapshot), false));
        }
    }

    /// <summary>Rejects missing domain identifiers.</summary>
    private static void ValidateId(string value) => ArgumentException.ThrowIfNullOrWhiteSpace(value);
    /// <summary>Rejects incomplete attachment persistence commands.</summary>
    private static void ValidateCommand(FormAttachmentPersistenceCommand command)
    {
        ArgumentNullException.ThrowIfNull(command); ArgumentNullException.ThrowIfNull(command.Attachment); ArgumentNullException.ThrowIfNull(command.Mutation); ArgumentException.ThrowIfNullOrWhiteSpace(command.Operation); ArgumentException.ThrowIfNullOrWhiteSpace(command.Fingerprint); ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.IdempotencyKey);
    }
}
