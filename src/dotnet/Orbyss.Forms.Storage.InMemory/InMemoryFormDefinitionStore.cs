using System.Runtime.CompilerServices;

namespace Orbyss.Forms;

/// <summary>Provides bounded process-local form-definition persistence with exact replay semantics.</summary>
public sealed class InMemoryFormDefinitionStore : IFormDefinitionStore
{
    /// <summary>Serializes all process-local aggregate reads and writes.</summary>
    private readonly object gate = new();
    /// <summary>Holds current aggregate state and replay history by form identifier.</summary>
    private readonly Dictionary<string, InMemoryFormDefinitionDocument> documents = new(StringComparer.Ordinal);
    /// <summary>Bounds aggregate and command counts.</summary>
    private readonly InMemoryFormStorageOptions options;
    /// <summary>Supplies server-observed audit timestamps.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Initializes an empty bounded store.</summary>
    public InMemoryFormDefinitionStore(InMemoryFormStorageOptions? options = null, TimeProvider? timeProvider = null)
    {
        this.options = options ?? new InMemoryFormStorageOptions();
        InMemoryFormStorageCodec.Validate(this.options);
        this.timeProvider = timeProvider ?? TimeProvider.System;
    }

    /// <inheritdoc />
    public ValueTask<FormDefinitionSnapshot?> GetAsync(FormId formId, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        ValidateId(formId);
        lock (gate) return ValueTask.FromResult(documents.TryGetValue(formId.Value, out var document) ? InMemoryFormStorageCodec.Clone<FormDefinitionSnapshot>(Snapshot(document)) : null);
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<FormDefinitionSnapshot> FindAsync([EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        FormDefinitionSnapshot[] found;
        lock (gate) found = documents.Values.Select(Snapshot).OrderBy(item => item.Definition.Name, StringComparer.OrdinalIgnoreCase).ThenBy(item => item.Definition.Id.Value, StringComparer.Ordinal).Select(InMemoryFormStorageCodec.Clone).ToArray();
        foreach (var snapshot in found) { cancellationToken.ThrowIfCancellationRequested(); yield return snapshot; await Task.Yield(); }
    }

    /// <inheritdoc />
    public ValueTask<FormDefinitionPersistenceResult?> ReplayAsync(FormId formId, string idempotencyKey, string fingerprint, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        ValidateId(formId);
        ArgumentException.ThrowIfNullOrWhiteSpace(idempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint);
        lock (gate)
        {
            if (!documents.TryGetValue(formId.Value, out var document) || !document.Commands.TryGetValue(idempotencyKey, out var replay)) return ValueTask.FromResult<FormDefinitionPersistenceResult?>(null);
            if (!string.Equals(replay.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form idempotency key was reused for a different command.");
            return ValueTask.FromResult<FormDefinitionPersistenceResult?>(new(InMemoryFormStorageCodec.Clone(replay.Snapshot), true));
        }
    }

    /// <inheritdoc />
    public ValueTask<FormDefinitionPersistenceResult> WriteAsync(FormDefinitionPersistenceCommand command, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        ValidateCommand(command);
        lock (gate)
        {
            documents.TryGetValue(command.Definition.Id.Value, out var current);
            if (current?.Commands.TryGetValue(command.Mutation.IdempotencyKey, out var replay) == true)
            {
                if (!string.Equals(replay.Fingerprint, command.Fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form idempotency key was reused for a different command.");
                return ValueTask.FromResult(new FormDefinitionPersistenceResult(InMemoryFormStorageCodec.Clone(replay.Snapshot), true));
            }
            if (command.RequireAbsent)
            {
                if (current is not null) throw new InvalidOperationException("The form definition already exists.");
                if (command.Mutation.ExpectedVersion is not null) throw new InvalidOperationException("A create command cannot supply an existing form version.");
                if (documents.Count >= options.MaximumDocuments) throw new InvalidOperationException("The in-memory form definition limit was reached.");
            }
            else if (current is null) throw new KeyNotFoundException("The form definition does not exist.");
            else if (command.Mutation.ExpectedVersion != current.Snapshot.Version) throw new InvalidOperationException("The form definition concurrency token does not match.");

            var definition = InMemoryFormStorageCodec.Clone(command.Definition);
            var candidate = command.Candidate is null ? null : InMemoryFormStorageCodec.Clone(command.Candidate);
            var evidence = command.Evidence.ToArray();
            var version = new FormConcurrencyToken(InMemoryFormStorageCodec.Hash(new { definition, candidate, evidence }));
            var audit = (current?.Snapshot.AuditTrail ?? []).Append(new FormDefinitionAuditEntry(command.Operation, command.Mutation.IdempotencyKey, command.Mutation.Actor, command.Mutation.RequestedAt, timeProvider.GetUtcNow(), command.Mutation.CorrelationId, current?.Snapshot.Version, version)).ToArray();
            var snapshot = new FormDefinitionSnapshot(definition, candidate, evidence, version, audit);
            var commands = current?.Commands.ToDictionary(item => item.Key, item => item.Value, StringComparer.Ordinal) ?? new Dictionary<string, InMemoryFormDefinitionReplay>(StringComparer.Ordinal);
            if (commands.Count >= options.MaximumCommandsPerDocument) throw new InvalidOperationException("The in-memory form command history limit was reached.");
            commands.Add(command.Mutation.IdempotencyKey, new InMemoryFormDefinitionReplay(command.Fingerprint, snapshot));
            var document = new InMemoryFormDefinitionDocument(snapshot, commands);
            InMemoryFormStorageCodec.EnsureSize(document, options.MaximumDocumentBytes);
            documents[definition.Id.Value] = document;
            return ValueTask.FromResult(new FormDefinitionPersistenceResult(InMemoryFormStorageCodec.Clone(snapshot), false));
        }
    }

    /// <summary>Projects the stored aggregate snapshot.</summary>
    private static FormDefinitionSnapshot Snapshot(InMemoryFormDefinitionDocument document) => document.Snapshot;
    /// <summary>Rejects missing identifiers before dictionary access.</summary>
    private static void ValidateId(FormId id) { ArgumentNullException.ThrowIfNull(id); ArgumentException.ThrowIfNullOrWhiteSpace(id.Value); }
    /// <summary>Rejects incomplete persistence commands.</summary>
    private static void ValidateCommand(FormDefinitionPersistenceCommand command)
    {
        ArgumentNullException.ThrowIfNull(command); ArgumentNullException.ThrowIfNull(command.Definition); ArgumentNullException.ThrowIfNull(command.Evidence); ArgumentNullException.ThrowIfNull(command.Mutation);
        ValidateId(command.Definition.Id); ArgumentException.ThrowIfNullOrWhiteSpace(command.Operation); ArgumentException.ThrowIfNullOrWhiteSpace(command.Fingerprint); ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.IdempotencyKey); ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.Actor.Id); ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.Actor.Kind);
        if (command.Mutation.RequestedAt == default) throw new ArgumentException("A form mutation timestamp is required.", nameof(command));
    }
}
