using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ProgramKit.Localization;

/// <summary>Stores current localization catalogs with atomic process-local writes and verified durable history.</summary>
public sealed class FileSystemLocalizationCatalogStore : ILocalizationCatalogStore
{
    /// <summary>Uses stable web serialization for content tokens and persistence.</summary>
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = false
    };

    /// <summary>Serializes writes to one catalog within the current process.</summary>
    private static readonly ConcurrentDictionary<string, SemaphoreSlim> WriteGates = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Holds the resolved consumer-owned catalog directory.</summary>
    private readonly string directoryPath;

    /// <summary>Bounds the complete verified document, including audit and replay history.</summary>
    private readonly int maximumDocumentBytes;

    /// <summary>Bounds filesystem enumeration work for one query.</summary>
    private readonly int maximumCatalogs;

    /// <summary>Supplies server-observed audit timestamps.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Initializes a bounded store rooted in an explicit consumer-owned directory.</summary>
    public FileSystemLocalizationCatalogStore(
        FileSystemLocalizationCatalogStoreOptions options,
        TimeProvider? timeProvider = null)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentException.ThrowIfNullOrWhiteSpace(options.DirectoryPath);
        if (options.MaximumDocumentBytes is < 1024 or > 268_435_456) throw new ArgumentOutOfRangeException(nameof(options), "The catalog document limit must be between 1 KiB and 256 MiB.");
        if (options.MaximumCatalogs is < 1 or > 1_000_000) throw new ArgumentOutOfRangeException(nameof(options), "The catalog count limit must be between 1 and 1,000,000.");
        directoryPath = Path.GetFullPath(options.DirectoryPath);
        maximumDocumentBytes = options.MaximumDocumentBytes;
        maximumCatalogs = options.MaximumCatalogs;
        this.timeProvider = timeProvider ?? TimeProvider.System;
        Directory.CreateDirectory(directoryPath);
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationCatalogSnapshot?> GetAsync(
        LocalizationCatalogId catalogId,
        CancellationToken cancellationToken = default)
    {
        ValidateId(catalogId);
        var path = CatalogPath(catalogId);
        if (!File.Exists(path)) return null;
        var document = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
        if (document.Catalog.Id != catalogId) throw new InvalidDataException($"Localization catalog document '{path}' does not match its requested identifier.");
        return Snapshot(document);
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<LocalizationCatalogSnapshot> FindAsync(
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var snapshots = new List<LocalizationCatalogSnapshot>();
        foreach (var path in Directory.EnumerateFiles(directoryPath, "*.localization-catalog.json", SearchOption.TopDirectoryOnly))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (snapshots.Count >= maximumCatalogs) throw new InvalidDataException("The localization catalog store exceeds its configured enumeration limit.");
            var document = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
            if (!string.Equals(Path.GetFileName(path), Hash(document.Catalog.Id.Value) + ".localization-catalog.json", StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException($"Localization catalog document '{path}' does not match its embedded identifier.");
            snapshots.Add(Snapshot(document));
        }

        foreach (var snapshot in snapshots.OrderBy(item => item.Catalog.Name, StringComparer.OrdinalIgnoreCase).ThenBy(item => item.Catalog.Id.Value, StringComparer.Ordinal))
        {
            yield return snapshot;
        }
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationCatalogPersistenceResult?> ReplayAsync(
        LocalizationCatalogId catalogId,
        string idempotencyKey,
        string fingerprint,
        CancellationToken cancellationToken = default)
    {
        ValidateId(catalogId);
        ArgumentException.ThrowIfNullOrWhiteSpace(idempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint);
        var path = CatalogPath(catalogId);
        var gate = WriteGates.GetOrAdd(path, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (!File.Exists(path)) return null;
            var current = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
            if (!current.Commands.TryGetValue(idempotencyKey, out var replay)) return null;
            if (!string.Equals(replay.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The localization idempotency key was reused for a different catalog command.");
            return new LocalizationCatalogPersistenceResult(
                new LocalizationCatalogSnapshot(replay.Catalog, replay.Version, current.AuditTrail.Take(replay.AuditCount).ToArray()),
                true);
        }
        finally
        {
            gate.Release();
        }
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationCatalogPersistenceResult> WriteAsync(
        LocalizationCatalogPersistenceCommand command,
        CancellationToken cancellationToken = default)
    {
        ValidateCommand(command);
        var path = CatalogPath(command.Catalog.Id);
        var gate = WriteGates.GetOrAdd(path, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var current = File.Exists(path) ? await ReadAsync(path, cancellationToken).ConfigureAwait(false) : null;
            if (current?.Commands.TryGetValue(command.Mutation.IdempotencyKey, out var replay) == true)
            {
                if (!string.Equals(replay.Fingerprint, command.Fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The localization idempotency key was reused for a different catalog command.");
                return new LocalizationCatalogPersistenceResult(
                    new LocalizationCatalogSnapshot(replay.Catalog, replay.Version, current.AuditTrail.Take(replay.AuditCount).ToArray()),
                    true);
            }

            RequireConcurrency(command, current);
            var previousVersion = current?.Version;
            var version = Version(command.Catalog);
            var audit = (current?.AuditTrail ?? []).Append(new LocalizationCatalogAuditEntry(
                command.Operation,
                command.Mutation.IdempotencyKey,
                command.Mutation.Actor,
                command.Mutation.RequestedAt,
                timeProvider.GetUtcNow(),
                command.Mutation.CorrelationId,
                previousVersion,
                version)).ToArray();
            var commands = current?.Commands.ToDictionary(item => item.Key, item => item.Value, StringComparer.Ordinal)
                ?? new Dictionary<string, StoredLocalizationCatalogCommand>(StringComparer.Ordinal);
            commands.Add(command.Mutation.IdempotencyKey, new StoredLocalizationCatalogCommand(command.Fingerprint, command.Catalog, version, audit.Length));
            var updated = new StoredLocalizationCatalogDocument(command.Catalog, version, audit, commands);
            await WriteDocumentAsync(path, updated, current is null, cancellationToken).ConfigureAwait(false);
            return new LocalizationCatalogPersistenceResult(Snapshot(updated), false);
        }
        finally
        {
            gate.Release();
        }
    }

    /// <summary>Requires create-versus-update and optimistic version semantics.</summary>
    private static void RequireConcurrency(
        LocalizationCatalogPersistenceCommand command,
        StoredLocalizationCatalogDocument? current)
    {
        if (command.RequireAbsent)
        {
            if (current is not null) throw new InvalidOperationException("The localization catalog already exists.");
            if (command.Mutation.ExpectedVersion is not null) throw new InvalidOperationException("A create command cannot supply an existing localization version.");
            return;
        }

        if (current is null) throw new KeyNotFoundException("The localization catalog does not exist.");
        if (command.Mutation.ExpectedVersion is null || !string.Equals(command.Mutation.ExpectedVersion.Value, current.Version.Value, StringComparison.Ordinal))
        {
            throw new InvalidOperationException("The localization catalog concurrency token does not match.");
        }
    }

    /// <summary>Writes a digest envelope through an atomic rename.</summary>
    private async ValueTask WriteDocumentAsync(
        string path,
        StoredLocalizationCatalogDocument document,
        bool create,
        CancellationToken cancellationToken)
    {
        var payload = JsonSerializer.Serialize(document, SerializerOptions);
        var content = Envelope(payload);
        if (Encoding.UTF8.GetByteCount(content) > maximumDocumentBytes) throw new InvalidOperationException("The localization catalog document exceeds the configured persistence limit.");
        var temporary = Path.Combine(directoryPath, $".{Path.GetFileName(path)}.{Guid.NewGuid():N}.tmp");
        try
        {
            await File.WriteAllTextAsync(temporary, content, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
            File.Move(temporary, path, overwrite: !create);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }

    /// <summary>Reads and verifies one stored catalog envelope.</summary>
    private async ValueTask<StoredLocalizationCatalogDocument> ReadAsync(
        string path,
        CancellationToken cancellationToken)
    {
        if (new FileInfo(path).Length > maximumDocumentBytes) throw new InvalidDataException($"Localization catalog document '{path}' exceeds its configured read limit.");
        var content = await File.ReadAllTextAsync(path, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
        var envelope = JsonNode.Parse(content)?.AsObject() ?? throw new InvalidDataException($"Localization catalog document '{path}' is invalid JSON.");
        var payload = envelope["payload"]?.GetValue<string>() ?? throw new InvalidDataException($"Localization catalog document '{path}' has no payload.");
        var digest = envelope["sha256"]?.GetValue<string>() ?? throw new InvalidDataException($"Localization catalog document '{path}' has no digest.");
        if (!string.Equals(digest, Hash(payload), StringComparison.Ordinal)) throw new InvalidDataException($"Localization catalog document '{path}' failed content verification.");
        var document = JsonSerializer.Deserialize<StoredLocalizationCatalogDocument>(payload, SerializerOptions)
            ?? throw new InvalidDataException($"Localization catalog document '{path}' has no catalog payload.");
        ValidateDocument(document, path);
        return document;
    }

    /// <summary>Validates version, audit, and replay invariants inside a verified document.</summary>
    private static void ValidateDocument(StoredLocalizationCatalogDocument document, string path)
    {
        if (document.Version != Version(document.Catalog)
            || document.AuditTrail.Count != document.Commands.Count
            || document.AuditTrail.Count == 0
            || document.AuditTrail[^1].Version != document.Version)
        {
            throw new InvalidDataException($"Localization catalog document '{path}' has inconsistent version or history metadata.");
        }

        foreach (var (key, command) in document.Commands)
        {
            if (string.IsNullOrWhiteSpace(key)
                || string.IsNullOrWhiteSpace(command.Fingerprint)
                || command.AuditCount is < 1
                || command.AuditCount > document.AuditTrail.Count
                || command.Version != Version(command.Catalog)
                || document.AuditTrail[command.AuditCount - 1].Version != command.Version)
            {
                throw new InvalidDataException($"Localization catalog document '{path}' has inconsistent replay metadata.");
            }
        }
    }

    /// <summary>Creates a public immutable view of a stored document.</summary>
    private static LocalizationCatalogSnapshot Snapshot(StoredLocalizationCatalogDocument document) =>
        new(document.Catalog, document.Version, document.AuditTrail.ToArray());

    /// <summary>Maps an untrusted catalog identifier to a fixed-length filename.</summary>
    private string CatalogPath(LocalizationCatalogId id) =>
        Path.Combine(directoryPath, Hash(id.Value) + ".localization-catalog.json");

    /// <summary>Creates the opaque content version for one catalog state.</summary>
    private static LocalizationConcurrencyToken Version(LocalizationCatalogDefinition catalog) =>
        new(Hash(JsonSerializer.Serialize(catalog, SerializerOptions)));

    /// <summary>Creates a digest envelope for one serialized payload.</summary>
    private static string Envelope(string payload) => new JsonObject
    {
        ["sha256"] = Hash(payload),
        ["payload"] = payload
    }.ToJsonString(SerializerOptions);

    /// <summary>Rejects missing or unsafe catalog command data before touching storage.</summary>
    private static void ValidateCommand(LocalizationCatalogPersistenceCommand command)
    {
        ArgumentNullException.ThrowIfNull(command);
        ArgumentNullException.ThrowIfNull(command.Catalog);
        ArgumentNullException.ThrowIfNull(command.Mutation);
        ValidateId(command.Catalog.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Operation);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Fingerprint);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.IdempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.Actor.Kind);
        if (command.Mutation.RequestedAt == default) throw new ArgumentException("A localization mutation timestamp is required.", nameof(command));
    }

    /// <summary>Rejects a missing catalog identifier.</summary>
    private static void ValidateId(LocalizationCatalogId catalogId)
    {
        ArgumentNullException.ThrowIfNull(catalogId);
        ArgumentException.ThrowIfNullOrWhiteSpace(catalogId.Value);
    }

    /// <summary>Computes a lowercase SHA-256 digest.</summary>
    private static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
