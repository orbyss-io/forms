using System.Collections.Concurrent;
using System.Runtime.CompilerServices;

namespace ProgramKit.Forms;

/// <summary>Stores draft/submission aggregates with process-local atomic writes and verified durable history.</summary>
public sealed class FileSystemFormSubmissionStore : IFormSubmissionStore
{
    /// <summary>Serializes process-local writes to each aggregate path.</summary>
    private static readonly ConcurrentDictionary<string, SemaphoreSlim> Gates = new(StringComparer.OrdinalIgnoreCase);
    /// <summary>Holds the response document directory.</summary>
    private readonly string directory;
    /// <summary>Bounds each verified document.</summary>
    private readonly int maximumDocumentBytes;
    /// <summary>Bounds query enumeration.</summary>
    private readonly int maximumDocuments;
    /// <summary>Bounds durable audit and replay history.</summary>
    private readonly int maximumCommands;
    /// <summary>Supplies server-observed audit timestamps.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Initializes a bounded store rooted in an explicit consumer-owned directory.</summary>
    public FileSystemFormSubmissionStore(FileSystemFormOperationalStoreOptions options, TimeProvider? timeProvider = null)
    {
        ArgumentNullException.ThrowIfNull(options);
        ValidateOptions(options);
        directory = Path.Combine(Path.GetFullPath(options.DirectoryPath), "responses");
        maximumDocumentBytes = options.MaximumDocumentBytes;
        maximumDocuments = options.MaximumDocuments;
        maximumCommands = options.MaximumCommandsPerDocument;
        this.timeProvider = timeProvider ?? TimeProvider.System;
        Directory.CreateDirectory(directory);
    }

    /// <inheritdoc />
    public async ValueTask<FormSubmissionAggregateSnapshot?> GetByDraftAsync(FormDraftId draftId, CancellationToken cancellationToken = default)
    {
        var path = PathFor(draftId);
        if (!File.Exists(path)) return null;
        return Snapshot(await ReadAsync(path, cancellationToken).ConfigureAwait(false));
    }

    /// <inheritdoc />
    public async ValueTask<FormSubmissionAggregateSnapshot?> GetBySubmissionAsync(FormSubmissionId submissionId, CancellationToken cancellationToken = default)
    {
        await foreach (var snapshot in FindAsync(cancellationToken).ConfigureAwait(false))
        {
            if (snapshot.Submission?.Id == submissionId) return snapshot;
        }
        return null;
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<FormSubmissionAggregateSnapshot> FindAsync([EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var count = 0;
        foreach (var path in Directory.EnumerateFiles(directory, "*.form-response.json", SearchOption.TopDirectoryOnly))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (++count > maximumDocuments) throw new InvalidDataException("The form response store exceeds its configured enumeration limit.");
            var document = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
            if (!string.Equals(Path.GetFileName(path), FileSystemVerifiedJson.Hash(document.Draft.Id.Value) + ".form-response.json", StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException($"Form response document '{path}' does not match its embedded identifier.");
            yield return Snapshot(document);
        }
    }

    /// <inheritdoc />
    public async ValueTask<FormSubmissionPersistenceResult?> ReplayAsync(FormDraftId draftId, string idempotencyKey, string fingerprint, CancellationToken cancellationToken = default)
    {
        var path = PathFor(draftId);
        if (!File.Exists(path)) return null;
        var document = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
        var command = document.Commands.SingleOrDefault(item => string.Equals(item.IdempotencyKey, idempotencyKey, StringComparison.Ordinal));
        if (command is null) return null;
        if (!string.Equals(command.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form operation idempotency key was already used with different input.");
        return new FormSubmissionPersistenceResult(command.Snapshot, true);
    }

    /// <inheritdoc />
    public async ValueTask<FormSubmissionPersistenceResult> PersistAsync(FormSubmissionPersistenceCommand command, CancellationToken cancellationToken = default)
    {
        ValidateCommand(command);
        var path = PathFor(command.Draft.Id);
        var gate = Gates.GetOrAdd(path, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            FormResponseDocument? current = File.Exists(path) ? await ReadAsync(path, cancellationToken).ConfigureAwait(false) : null;
            var replay = current?.Commands.SingleOrDefault(item => string.Equals(item.IdempotencyKey, command.Mutation.IdempotencyKey, StringComparison.Ordinal));
            if (replay is not null)
            {
                if (!string.Equals(replay.Fingerprint, command.Fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form operation idempotency key was already used with different input.");
                return new FormSubmissionPersistenceResult(replay.Snapshot, true);
            }
            if (command.RequireAbsent)
            {
                if (current is not null) throw new InvalidOperationException("The form draft already exists.");
            }
            else
            {
                if (current is null) throw new InvalidOperationException("The form draft does not exist.");
                if (!string.Equals(command.Mutation.ExpectedVersion?.Value, current.Version, StringComparison.Ordinal)) throw new InvalidOperationException("The form response changed since it was read.");
            }
            var audit = (current?.Audit ?? []).Append(new FormOperationalAuditEntry(command.Operation, command.Mutation.IdempotencyKey, command.Fingerprint, command.Mutation.Actor, command.Mutation.RequestedAt, timeProvider.GetUtcNow(), command.Mutation.CorrelationId)).ToArray();
            var version = Version(command.Draft, command.Submission, audit);
            var snapshot = new FormSubmissionAggregateSnapshot(command.Draft, command.Submission, new FormConcurrencyToken(version), audit);
            var commands = (current?.Commands ?? []).Append(new FormResponseCommand(command.Mutation.IdempotencyKey, command.Fingerprint, snapshot)).ToArray();
            if (commands.Length > maximumCommands) throw new InvalidOperationException("The form response command history exceeds its configured limit.");
            var next = new FormResponseDocument(command.Draft, command.Submission, version, audit, commands);
            await FileSystemVerifiedJson.WriteAsync(path, next, maximumDocumentBytes, cancellationToken).ConfigureAwait(false);
            return new FormSubmissionPersistenceResult(snapshot, false);
        }
        finally
        {
            gate.Release();
        }
    }

    /// <summary>Maps an untrusted draft identifier to a fixed-length filename.</summary>
    private string PathFor(FormDraftId id) => Path.Combine(directory, FileSystemVerifiedJson.Hash(RequiredId(id.Value)) + ".form-response.json");
    /// <summary>Reads and verifies aggregate history and content version.</summary>
    private async ValueTask<FormResponseDocument> ReadAsync(string path, CancellationToken cancellationToken)
    {
        var document = await FileSystemVerifiedJson.ReadAsync<FormResponseDocument>(path, maximumDocumentBytes, cancellationToken).ConfigureAwait(false);
        if (document.Audit.Count != document.Commands.Count || document.Commands.Count > maximumCommands || !string.Equals(document.Version, Version(document.Draft, document.Submission, document.Audit), StringComparison.Ordinal)) throw new InvalidDataException($"Form response document '{path}' has invalid internal history.");
        return document;
    }
    /// <summary>Projects persisted state without exposing its envelope.</summary>
    private static FormSubmissionAggregateSnapshot Snapshot(FormResponseDocument document) => new(document.Draft, document.Submission, new FormConcurrencyToken(document.Version), document.Audit);
    /// <summary>Computes the opaque aggregate version over state and audit history.</summary>
    private static string Version(FormDraft draft, FormSubmission? submission, IReadOnlyList<FormOperationalAuditEntry> audit) => FileSystemVerifiedJson.Hash(System.Text.Json.JsonSerializer.Serialize(new { draft, submission, audit }, FileSystemVerifiedJson.Options));
    /// <summary>Requires a nonempty identifier before hashing.</summary>
    private static string RequiredId(string value) { if (string.IsNullOrWhiteSpace(value)) throw new ArgumentException("A form identifier is required."); return value; }

    /// <summary>Rejects incomplete or cross-aggregate persistence commands.</summary>
    private static void ValidateCommand(FormSubmissionPersistenceCommand command)
    {
        ArgumentNullException.ThrowIfNull(command);
        ArgumentNullException.ThrowIfNull(command.Draft);
        ArgumentNullException.ThrowIfNull(command.Mutation);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Operation);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Fingerprint);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.IdempotencyKey);
        if (command.Submission is not null && command.Submission.DraftId != command.Draft.Id) throw new ArgumentException("A submission must belong to the persisted draft.", nameof(command));
    }

    /// <summary>Rejects unsafe filesystem document and history bounds.</summary>
    private static void ValidateOptions(FileSystemFormOperationalStoreOptions options)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(options.DirectoryPath);
        if (options.MaximumDocumentBytes is < 4096 or > 268_435_456 || options.MaximumDocuments is < 1 or > 1_000_000 || options.MaximumCommandsPerDocument is < 1 or > 100_000) throw new ArgumentOutOfRangeException(nameof(options), "Filesystem form store bounds are invalid.");
    }
}
