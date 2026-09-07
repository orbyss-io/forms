using System.Runtime.CompilerServices;

namespace Orbyss.Localization;

/// <summary>Provides process-local catalog persistence with exact replay and audit semantics.</summary>
public sealed class InMemoryLocalizationCatalogStore : ILocalizationCatalogStore
{
    /// <summary>Serializes catalog reads and writes.</summary>
    private readonly object gate = new();
    /// <summary>Holds current catalog state and replay history by identifier.</summary>
    private readonly Dictionary<string, InMemoryLocalizationCatalogDocument> documents = new(StringComparer.Ordinal);
    /// <summary>Bounds catalog and command counts.</summary>
    private readonly InMemoryLocalizationStorageOptions options;
    /// <summary>Supplies server-observed audit timestamps.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Initializes an empty bounded catalog store.</summary>
    public InMemoryLocalizationCatalogStore(InMemoryLocalizationStorageOptions? options = null, TimeProvider? timeProvider = null)
    {
        this.options = options ?? new InMemoryLocalizationStorageOptions(); InMemoryLocalizationStorageCodec.Validate(this.options); this.timeProvider = timeProvider ?? TimeProvider.System;
    }

    /// <inheritdoc />
    public ValueTask<LocalizationCatalogSnapshot?> GetAsync(LocalizationCatalogId catalogId, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(catalogId);
        lock (gate) return ValueTask.FromResult(documents.TryGetValue(catalogId.Value, out var document) ? InMemoryLocalizationStorageCodec.Clone<LocalizationCatalogSnapshot>(document.Snapshot) : null);
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<LocalizationCatalogSnapshot> FindAsync([EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        LocalizationCatalogSnapshot[] found;
        lock (gate) found = documents.Values.Select(item => InMemoryLocalizationStorageCodec.Clone(item.Snapshot)).OrderBy(item => item.Catalog.Name, StringComparer.OrdinalIgnoreCase).ThenBy(item => item.Catalog.Id.Value, StringComparer.Ordinal).ToArray();
        foreach (var snapshot in found) { cancellationToken.ThrowIfCancellationRequested(); yield return snapshot; await Task.Yield(); }
    }

    /// <inheritdoc />
    public ValueTask<LocalizationCatalogPersistenceResult?> ReplayAsync(LocalizationCatalogId catalogId, string idempotencyKey, string fingerprint, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(catalogId); ArgumentException.ThrowIfNullOrWhiteSpace(idempotencyKey); ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint);
        lock (gate)
        {
            if (!documents.TryGetValue(catalogId.Value, out var document) || !document.Commands.TryGetValue(idempotencyKey, out var replay)) return ValueTask.FromResult<LocalizationCatalogPersistenceResult?>(null);
            if (!string.Equals(replay.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The localization idempotency key was reused for a different catalog command.");
            return ValueTask.FromResult<LocalizationCatalogPersistenceResult?>(new(InMemoryLocalizationStorageCodec.Clone(replay.Snapshot), true));
        }
    }

    /// <inheritdoc />
    public ValueTask<LocalizationCatalogPersistenceResult> WriteAsync(LocalizationCatalogPersistenceCommand command, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateCommand(command);
        lock (gate)
        {
            documents.TryGetValue(command.Catalog.Id.Value, out var current);
            if (current?.Commands.TryGetValue(command.Mutation.IdempotencyKey, out var replay) == true)
            {
                if (!string.Equals(replay.Fingerprint, command.Fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The localization idempotency key was reused for a different catalog command.");
                return ValueTask.FromResult(new LocalizationCatalogPersistenceResult(InMemoryLocalizationStorageCodec.Clone(replay.Snapshot), true));
            }
            if (command.RequireAbsent)
            {
                if (current is not null) throw new InvalidOperationException("The localization catalog already exists.");
                if (command.Mutation.ExpectedVersion is not null) throw new InvalidOperationException("A create command cannot supply an existing localization version.");
                if (documents.Count >= options.MaximumDocuments) throw new InvalidOperationException("The in-memory localization catalog limit was reached.");
            }
            else if (current is null) throw new KeyNotFoundException("The localization catalog does not exist.");
            else if (command.Mutation.ExpectedVersion != current.Snapshot.Version) throw new InvalidOperationException("The localization catalog concurrency token does not match.");

            var catalog = InMemoryLocalizationStorageCodec.Clone(command.Catalog);
            var version = new LocalizationConcurrencyToken(InMemoryLocalizationStorageCodec.Hash(catalog));
            var audit = (current?.Snapshot.AuditTrail ?? []).Append(new LocalizationCatalogAuditEntry(command.Operation, command.Mutation.IdempotencyKey, command.Mutation.Actor, command.Mutation.RequestedAt, timeProvider.GetUtcNow(), command.Mutation.CorrelationId, current?.Snapshot.Version, version)).ToArray();
            var snapshot = new LocalizationCatalogSnapshot(catalog, version, audit);
            var commands = current?.Commands.ToDictionary(item => item.Key, item => item.Value, StringComparer.Ordinal) ?? new Dictionary<string, InMemoryLocalizationCatalogReplay>(StringComparer.Ordinal);
            if (commands.Count >= options.MaximumCommandsPerCatalog) throw new InvalidOperationException("The in-memory localization command history limit was reached.");
            commands.Add(command.Mutation.IdempotencyKey, new InMemoryLocalizationCatalogReplay(command.Fingerprint, snapshot));
            var document = new InMemoryLocalizationCatalogDocument(snapshot, commands);
            InMemoryLocalizationStorageCodec.EnsureSize(document, options.MaximumDocumentBytes);
            documents[catalog.Id.Value] = document;
            return ValueTask.FromResult(new LocalizationCatalogPersistenceResult(InMemoryLocalizationStorageCodec.Clone(snapshot), false));
        }
    }

    /// <summary>Rejects missing catalog identifiers.</summary>
    private static void ValidateId(LocalizationCatalogId id) { ArgumentNullException.ThrowIfNull(id); ArgumentException.ThrowIfNullOrWhiteSpace(id.Value); }
    /// <summary>Rejects incomplete catalog persistence commands.</summary>
    private static void ValidateCommand(LocalizationCatalogPersistenceCommand command)
    {
        ArgumentNullException.ThrowIfNull(command); ArgumentNullException.ThrowIfNull(command.Catalog); ArgumentNullException.ThrowIfNull(command.Mutation); ValidateId(command.Catalog.Id); ArgumentException.ThrowIfNullOrWhiteSpace(command.Operation); ArgumentException.ThrowIfNullOrWhiteSpace(command.Fingerprint); ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.IdempotencyKey); ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.Actor.Id); ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.Actor.Kind);
        if (command.Mutation.RequestedAt == default) throw new ArgumentException("A localization mutation timestamp is required.", nameof(command));
    }
}
