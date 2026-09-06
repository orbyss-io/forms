using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ProgramKit.Forms;

/// <summary>Stores editable form aggregates with verified atomic writes and durable command replay.</summary>
public sealed class FileSystemFormDefinitionStore : IFormDefinitionStore
{
    /// <summary>Uses stable web serialization for versioning and persistence.</summary>
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web) { WriteIndented = false };
    /// <summary>Serializes writes to one definition in the current process.</summary>
    private static readonly ConcurrentDictionary<string, SemaphoreSlim> WriteGates = new(StringComparer.OrdinalIgnoreCase);
    /// <summary>Holds the resolved consumer-owned directory.</summary>
    private readonly string directoryPath;
    /// <summary>Bounds each complete verified aggregate document.</summary>
    private readonly int maximumDocumentBytes;
    /// <summary>Bounds work performed during enumeration.</summary>
    private readonly int maximumForms;
    /// <summary>Supplies server-observed audit timestamps.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Initializes a bounded store rooted in an explicit consumer-owned directory.</summary>
    public FileSystemFormDefinitionStore(FileSystemFormDefinitionStoreOptions options, TimeProvider? timeProvider = null)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentException.ThrowIfNullOrWhiteSpace(options.DirectoryPath);
        if (options.MaximumDocumentBytes is < 1024 or > 268_435_456) throw new ArgumentOutOfRangeException(nameof(options), "The form document limit must be between 1 KiB and 256 MiB.");
        if (options.MaximumForms is < 1 or > 1_000_000) throw new ArgumentOutOfRangeException(nameof(options), "The form count limit must be between 1 and 1,000,000.");
        directoryPath = Path.GetFullPath(options.DirectoryPath);
        maximumDocumentBytes = options.MaximumDocumentBytes;
        maximumForms = options.MaximumForms;
        this.timeProvider = timeProvider ?? TimeProvider.System;
        Directory.CreateDirectory(directoryPath);
    }

    /// <inheritdoc />
    public async ValueTask<FormDefinitionSnapshot?> GetAsync(FormId formId, CancellationToken cancellationToken = default)
    {
        ValidateId(formId);
        var path = DefinitionPath(formId);
        if (!File.Exists(path)) return null;
        var document = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
        if (document.Definition.Id != formId) throw new InvalidDataException($"Form definition document '{path}' does not match its requested identifier.");
        return Snapshot(document);
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<FormDefinitionSnapshot> FindAsync([EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var snapshots = new List<FormDefinitionSnapshot>();
        foreach (var path in Directory.EnumerateFiles(directoryPath, "*.form-definition.json", SearchOption.TopDirectoryOnly))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (snapshots.Count >= maximumForms) throw new InvalidDataException("The form definition store exceeds its configured enumeration limit.");
            var document = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
            if (!string.Equals(Path.GetFileName(path), Hash(document.Definition.Id.Value) + ".form-definition.json", StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException($"Form definition document '{path}' does not match its embedded identifier.");
            snapshots.Add(Snapshot(document));
        }

        foreach (var snapshot in snapshots.OrderBy(item => item.Definition.Name, StringComparer.OrdinalIgnoreCase).ThenBy(item => item.Definition.Id.Value, StringComparer.Ordinal)) yield return snapshot;
    }

    /// <inheritdoc />
    public async ValueTask<FormDefinitionPersistenceResult?> ReplayAsync(FormId formId, string idempotencyKey, string fingerprint, CancellationToken cancellationToken = default)
    {
        ValidateId(formId);
        ArgumentException.ThrowIfNullOrWhiteSpace(idempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint);
        var path = DefinitionPath(formId);
        var gate = WriteGates.GetOrAdd(path, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (!File.Exists(path)) return null;
            var current = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
            if (!current.Commands.TryGetValue(idempotencyKey, out var replay)) return null;
            if (!string.Equals(replay.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form idempotency key was reused for a different command.");
            return new FormDefinitionPersistenceResult(Snapshot(replay, current.AuditTrail), true);
        }
        finally { gate.Release(); }
    }

    /// <inheritdoc />
    public async ValueTask<FormDefinitionPersistenceResult> WriteAsync(FormDefinitionPersistenceCommand command, CancellationToken cancellationToken = default)
    {
        ValidateCommand(command);
        var path = DefinitionPath(command.Definition.Id);
        var gate = WriteGates.GetOrAdd(path, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var current = File.Exists(path) ? await ReadAsync(path, cancellationToken).ConfigureAwait(false) : null;
            if (current?.Commands.TryGetValue(command.Mutation.IdempotencyKey, out var replay) == true)
            {
                if (!string.Equals(replay.Fingerprint, command.Fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form idempotency key was reused for a different command.");
                return new FormDefinitionPersistenceResult(Snapshot(replay, current.AuditTrail), true);
            }

            RequireConcurrency(command, current);
            var previousVersion = current?.Version;
            var version = Version(command.Definition, command.Candidate, command.Evidence);
            var audit = (current?.AuditTrail ?? []).Append(new FormDefinitionAuditEntry(command.Operation, command.Mutation.IdempotencyKey, command.Mutation.Actor, command.Mutation.RequestedAt, timeProvider.GetUtcNow(), command.Mutation.CorrelationId, previousVersion, version)).ToArray();
            var commands = current?.Commands.ToDictionary(item => item.Key, item => item.Value, StringComparer.Ordinal) ?? new Dictionary<string, StoredFormDefinitionCommand>(StringComparer.Ordinal);
            commands.Add(command.Mutation.IdempotencyKey, new StoredFormDefinitionCommand(command.Fingerprint, command.Definition, command.Candidate, command.Evidence.ToArray(), version, audit.Length));
            var updated = new StoredFormDefinitionDocument(command.Definition, command.Candidate, command.Evidence.ToArray(), version, audit, commands);
            await WriteDocumentAsync(path, updated, current is null, cancellationToken).ConfigureAwait(false);
            return new FormDefinitionPersistenceResult(Snapshot(updated), false);
        }
        finally { gate.Release(); }
    }

    /// <summary>Requires create-versus-update and opaque optimistic concurrency.</summary>
    private static void RequireConcurrency(FormDefinitionPersistenceCommand command, StoredFormDefinitionDocument? current)
    {
        if (command.RequireAbsent)
        {
            if (current is not null) throw new InvalidOperationException("The form definition already exists.");
            if (command.Mutation.ExpectedVersion is not null) throw new InvalidOperationException("A create command cannot supply an existing form version.");
            return;
        }
        if (current is null) throw new KeyNotFoundException("The form definition does not exist.");
        if (command.Mutation.ExpectedVersion is null || command.Mutation.ExpectedVersion != current.Version) throw new InvalidOperationException("The form definition concurrency token does not match.");
    }

    /// <summary>Writes one bounded digest envelope through an atomic rename.</summary>
    private async ValueTask WriteDocumentAsync(string path, StoredFormDefinitionDocument document, bool create, CancellationToken cancellationToken)
    {
        var payload = JsonSerializer.Serialize(document, SerializerOptions);
        var content = Envelope(payload);
        if (Encoding.UTF8.GetByteCount(content) > maximumDocumentBytes) throw new InvalidOperationException("The form definition document exceeds the configured persistence limit.");
        var temporary = Path.Combine(directoryPath, $".{Path.GetFileName(path)}.{Guid.NewGuid():N}.tmp");
        try
        {
            await File.WriteAllTextAsync(temporary, content, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
            File.Move(temporary, path, overwrite: !create);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    /// <summary>Reads and verifies one stored aggregate envelope.</summary>
    private async ValueTask<StoredFormDefinitionDocument> ReadAsync(string path, CancellationToken cancellationToken)
    {
        if (new FileInfo(path).Length > maximumDocumentBytes) throw new InvalidDataException($"Form definition document '{path}' exceeds its configured read limit.");
        var content = await File.ReadAllTextAsync(path, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
        var envelope = JsonNode.Parse(content)?.AsObject() ?? throw new InvalidDataException($"Form definition document '{path}' is invalid JSON.");
        var payload = envelope["payload"]?.GetValue<string>() ?? throw new InvalidDataException($"Form definition document '{path}' has no payload.");
        var digest = envelope["sha256"]?.GetValue<string>() ?? throw new InvalidDataException($"Form definition document '{path}' has no digest.");
        if (!string.Equals(digest, Hash(payload), StringComparison.Ordinal)) throw new InvalidDataException($"Form definition document '{path}' failed content verification.");
        var document = JsonSerializer.Deserialize<StoredFormDefinitionDocument>(payload, SerializerOptions) ?? throw new InvalidDataException($"Form definition document '{path}' has no aggregate payload.");
        ValidateDocument(document, path);
        return document;
    }

    /// <summary>Validates version, audit, and replay invariants.</summary>
    private static void ValidateDocument(StoredFormDefinitionDocument document, string path)
    {
        if (document.Version != Version(document.Definition, document.Candidate, document.Evidence) || document.AuditTrail.Count != document.Commands.Count || document.AuditTrail.Count == 0 || document.AuditTrail[^1].Version != document.Version) throw new InvalidDataException($"Form definition document '{path}' has inconsistent version or history metadata.");
        foreach (var (key, command) in document.Commands)
        {
            if (string.IsNullOrWhiteSpace(key) || string.IsNullOrWhiteSpace(command.Fingerprint) || command.AuditCount is < 1 || command.AuditCount > document.AuditTrail.Count || command.Version != Version(command.Definition, command.Candidate, command.Evidence) || document.AuditTrail[command.AuditCount - 1].Version != command.Version) throw new InvalidDataException($"Form definition document '{path}' has inconsistent replay metadata.");
        }
    }

    /// <summary>Projects a current stored document.</summary>
    private static FormDefinitionSnapshot Snapshot(StoredFormDefinitionDocument document) => new(document.Definition, document.Candidate, document.Evidence.ToArray(), document.Version, document.AuditTrail.ToArray());
    /// <summary>Projects the historical result bound to a command replay.</summary>
    private static FormDefinitionSnapshot Snapshot(StoredFormDefinitionCommand command, IReadOnlyList<FormDefinitionAuditEntry> audit) => new(command.Definition, command.Candidate, command.Evidence.ToArray(), command.Version, audit.Take(command.AuditCount).ToArray());
    /// <summary>Maps an untrusted identifier to a fixed-length filename.</summary>
    private string DefinitionPath(FormId id) => Path.Combine(directoryPath, Hash(id.Value) + ".form-definition.json");
    /// <summary>Creates the opaque aggregate content version.</summary>
    private static FormConcurrencyToken Version(FormDefinition definition, FormCandidate? candidate, IReadOnlyList<string> evidence) => new(Hash(JsonSerializer.Serialize(new { definition, candidate, evidence }, SerializerOptions)));
    /// <summary>Creates a content-digest envelope.</summary>
    private static string Envelope(string payload) => new JsonObject { ["sha256"] = Hash(payload), ["payload"] = payload }.ToJsonString(SerializerOptions);

    /// <summary>Rejects incomplete or unsafe command data before storage access.</summary>
    private static void ValidateCommand(FormDefinitionPersistenceCommand command)
    {
        ArgumentNullException.ThrowIfNull(command);
        ArgumentNullException.ThrowIfNull(command.Definition);
        ArgumentNullException.ThrowIfNull(command.Evidence);
        ArgumentNullException.ThrowIfNull(command.Mutation);
        ValidateId(command.Definition.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Operation);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Fingerprint);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.IdempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.Actor.Kind);
        if (command.Mutation.RequestedAt == default) throw new ArgumentException("A form mutation timestamp is required.", nameof(command));
    }

    /// <summary>Rejects a missing form identifier.</summary>
    private static void ValidateId(FormId id) { ArgumentNullException.ThrowIfNull(id); ArgumentException.ThrowIfNullOrWhiteSpace(id.Value); }
    /// <summary>Computes a lowercase SHA-256 digest.</summary>
    private static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
