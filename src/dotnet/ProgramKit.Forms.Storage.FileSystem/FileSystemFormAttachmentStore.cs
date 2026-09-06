using System.Collections.Concurrent;
using System.Runtime.CompilerServices;

namespace ProgramKit.Forms;

/// <summary>Stores attachment metadata and durable command history independently from binary content.</summary>
public sealed class FileSystemFormAttachmentStore : IFormAttachmentStore
{
    /// <summary>Serializes process-local writes to each metadata path.</summary>
    private static readonly ConcurrentDictionary<string, SemaphoreSlim> Gates = new(StringComparer.OrdinalIgnoreCase);
    /// <summary>Holds the attachment metadata directory.</summary>
    private readonly string directory;
    /// <summary>Bounds each verified metadata document.</summary>
    private readonly int maximumDocumentBytes;
    /// <summary>Bounds metadata enumeration work.</summary>
    private readonly int maximumDocuments;
    /// <summary>Bounds durable audit and replay history.</summary>
    private readonly int maximumCommands;
    /// <summary>Supplies server-observed audit timestamps.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Initializes a bounded metadata store rooted in an explicit consumer-owned directory.</summary>
    public FileSystemFormAttachmentStore(FileSystemFormOperationalStoreOptions options, TimeProvider? timeProvider = null)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentException.ThrowIfNullOrWhiteSpace(options.DirectoryPath);
        if (options.MaximumDocumentBytes is < 4096 or > 268_435_456 || options.MaximumDocuments is < 1 or > 1_000_000 || options.MaximumCommandsPerDocument is < 1 or > 100_000) throw new ArgumentOutOfRangeException(nameof(options), "Filesystem form store bounds are invalid.");
        directory = Path.Combine(Path.GetFullPath(options.DirectoryPath), "attachment-metadata");
        maximumDocumentBytes = options.MaximumDocumentBytes;
        maximumDocuments = options.MaximumDocuments;
        maximumCommands = options.MaximumCommandsPerDocument;
        this.timeProvider = timeProvider ?? TimeProvider.System;
        Directory.CreateDirectory(directory);
    }

    /// <inheritdoc />
    public async ValueTask<FormAttachmentSnapshot?> GetAsync(FormAttachmentId attachmentId, CancellationToken cancellationToken = default)
    {
        var path = PathFor(attachmentId);
        if (!File.Exists(path)) return null;
        return Snapshot(await ReadAsync(path, cancellationToken).ConfigureAwait(false));
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<FormAttachmentSnapshot> FindByDraftAsync(FormDraftId draftId, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var count = 0;
        foreach (var path in Directory.EnumerateFiles(directory, "*.form-attachment.json", SearchOption.TopDirectoryOnly))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (++count > maximumDocuments) throw new InvalidDataException("The form attachment store exceeds its configured enumeration limit.");
            var document = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
            if (document.Attachment.DraftId == draftId) yield return Snapshot(document);
        }
    }

    /// <inheritdoc />
    public async ValueTask<FormAttachmentPersistenceResult?> ReplayAsync(FormAttachmentId attachmentId, string idempotencyKey, string fingerprint, CancellationToken cancellationToken = default)
    {
        var path = PathFor(attachmentId);
        if (!File.Exists(path)) return null;
        var document = await ReadAsync(path, cancellationToken).ConfigureAwait(false);
        var replay = document.Commands.SingleOrDefault(item => string.Equals(item.IdempotencyKey, idempotencyKey, StringComparison.Ordinal));
        if (replay is null) return null;
        if (!string.Equals(replay.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The attachment idempotency key was already used with different input.");
        return new FormAttachmentPersistenceResult(replay.Snapshot, true);
    }

    /// <inheritdoc />
    public async ValueTask<FormAttachmentPersistenceResult> PersistAsync(FormAttachmentPersistenceCommand command, CancellationToken cancellationToken = default)
    {
        ValidateCommand(command);
        var path = PathFor(command.Attachment.Id);
        var gate = Gates.GetOrAdd(path, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            FormAttachmentMetadataDocument? current = File.Exists(path) ? await ReadAsync(path, cancellationToken).ConfigureAwait(false) : null;
            var replay = current?.Commands.SingleOrDefault(item => string.Equals(item.IdempotencyKey, command.Mutation.IdempotencyKey, StringComparison.Ordinal));
            if (replay is not null)
            {
                if (!string.Equals(replay.Fingerprint, command.Fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The attachment idempotency key was already used with different input.");
                return new FormAttachmentPersistenceResult(replay.Snapshot, true);
            }
            if (command.RequireAbsent)
            {
                if (current is not null) throw new InvalidOperationException("The attachment identifier already exists.");
            }
            else
            {
                if (current is null) throw new InvalidOperationException("The attachment does not exist.");
                if (!string.Equals(command.Mutation.ExpectedVersion?.Value, current.Version, StringComparison.Ordinal)) throw new InvalidOperationException("The attachment changed since it was read.");
            }
            var audit = (current?.Audit ?? []).Append(new FormOperationalAuditEntry(command.Operation, command.Mutation.IdempotencyKey, command.Fingerprint, command.Mutation.Actor, command.Mutation.RequestedAt, timeProvider.GetUtcNow(), command.Mutation.CorrelationId)).ToArray();
            var version = Version(command.Attachment, command.ContentKey, audit);
            var snapshot = new FormAttachmentSnapshot(command.Attachment, command.ContentKey, new FormConcurrencyToken(version));
            var commands = (current?.Commands ?? []).Append(new FormAttachmentMetadataCommand(command.Mutation.IdempotencyKey, command.Fingerprint, snapshot)).ToArray();
            if (commands.Length > maximumCommands) throw new InvalidOperationException("The attachment command history exceeds its configured limit.");
            await FileSystemVerifiedJson.WriteAsync(path, new FormAttachmentMetadataDocument(command.Attachment, command.ContentKey, version, audit, commands), maximumDocumentBytes, cancellationToken).ConfigureAwait(false);
            return new FormAttachmentPersistenceResult(snapshot, false);
        }
        finally
        {
            gate.Release();
        }
    }

    /// <summary>Maps an untrusted attachment identifier to a fixed-length filename.</summary>
    private string PathFor(FormAttachmentId id)
    {
        ArgumentNullException.ThrowIfNull(id);
        ArgumentException.ThrowIfNullOrWhiteSpace(id.Value);
        return Path.Combine(directory, FileSystemVerifiedJson.Hash(id.Value) + ".form-attachment.json");
    }
    /// <summary>Reads and verifies metadata history and content version.</summary>
    private async ValueTask<FormAttachmentMetadataDocument> ReadAsync(string path, CancellationToken cancellationToken)
    {
        var document = await FileSystemVerifiedJson.ReadAsync<FormAttachmentMetadataDocument>(path, maximumDocumentBytes, cancellationToken).ConfigureAwait(false);
        if (document.Audit.Count != document.Commands.Count || document.Commands.Count > maximumCommands || !string.Equals(document.Version, Version(document.Attachment, document.ContentKey, document.Audit), StringComparison.Ordinal)) throw new InvalidDataException($"Attachment document '{path}' has invalid internal history.");
        return document;
    }
    /// <summary>Projects persisted metadata without exposing its envelope.</summary>
    private static FormAttachmentSnapshot Snapshot(FormAttachmentMetadataDocument document) => new(document.Attachment, document.ContentKey, new FormConcurrencyToken(document.Version));
    /// <summary>Computes the opaque metadata version over state and audit history.</summary>
    private static string Version(FormAttachment attachment, string? contentKey, IReadOnlyList<FormOperationalAuditEntry> audit) => FileSystemVerifiedJson.Hash(System.Text.Json.JsonSerializer.Serialize(new { attachment, contentKey, audit }, FileSystemVerifiedJson.Options));
    /// <summary>Rejects incomplete attachment persistence commands.</summary>
    private static void ValidateCommand(FormAttachmentPersistenceCommand command)
    {
        ArgumentNullException.ThrowIfNull(command);
        ArgumentNullException.ThrowIfNull(command.Attachment);
        ArgumentNullException.ThrowIfNull(command.Mutation);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Operation);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Fingerprint);
        ArgumentException.ThrowIfNullOrWhiteSpace(command.Mutation.IdempotencyKey);
    }
}
