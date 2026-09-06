using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ProgramKit.Forms;

/// <summary>Orchestrates owner-scoped quarantine, signature checks, malware scanning, promotion, and removal.</summary>
public sealed class DefaultFormAttachmentService : IFormAttachmentOperations
{
    /// <summary>Provides stable web serialization for durable command fingerprints.</summary>
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);
    /// <summary>Persists auditable attachment metadata.</summary>
    private readonly IFormAttachmentStore store;
    /// <summary>Owns quarantine and available binary content.</summary>
    private readonly IFormAttachmentContentStore contentStore;
    /// <summary>Provides owner and active-state checks for target drafts.</summary>
    private readonly IFormSubmissionStore drafts;
    /// <summary>Enforces declaration, size, and content-signature allowlists.</summary>
    private readonly IFormAttachmentPolicy policy;
    /// <summary>Provides the selected fail-closed malware verdict.</summary>
    private readonly IFormAttachmentScanner scanner;
    /// <summary>Supplies server-observed audit timestamps.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Initializes fail-closed attachment orchestration over selected metadata, content, policy, and scanner providers.</summary>
    public DefaultFormAttachmentService(IFormAttachmentStore store, IFormAttachmentContentStore contentStore, IFormSubmissionStore drafts, IFormAttachmentPolicy policy, IFormAttachmentScanner scanner, TimeProvider? timeProvider = null)
    {
        this.store = store ?? throw new ArgumentNullException(nameof(store));
        this.contentStore = contentStore ?? throw new ArgumentNullException(nameof(contentStore));
        this.drafts = drafts ?? throw new ArgumentNullException(nameof(drafts));
        this.policy = policy ?? throw new ArgumentNullException(nameof(policy));
        this.scanner = scanner ?? throw new ArgumentNullException(nameof(scanner));
        this.timeProvider = timeProvider ?? TimeProvider.System;
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormAttachment>> UploadAsync(FormAttachmentId attachmentId, FormDraftId draftId, string fileName, string mediaType, Stream content, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(content);
        ValidateMutation(mutation, expected: false);
        policy.ValidateDeclaration(fileName, mediaType);
        var draft = await drafts.GetByDraftAsync(draftId, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The form draft does not exist.");
        RequireOwner(draft.Draft.OwnerId, mutation.Actor);
        if (draft.Draft.State != FormDraftState.Active) throw new InvalidOperationException("Attachments can only be uploaded to an active draft.");
        var written = await contentStore.WriteQuarantinedAsync(attachmentId, content, policy.MaximumBytes, policy.InspectionPrefixBytes, cancellationToken).ConfigureAwait(false);
        var fingerprint = Fingerprint("upload-attachment", new { attachmentId, draftId, fileName, mediaType, written.Length, written.Sha256 }, mutation);
        var replay = await store.ReplayAsync(attachmentId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null)
        {
            await contentStore.DeleteAsync(written.ContentKey, cancellationToken).ConfigureAwait(false);
            return Result(replay);
        }
        var now = timeProvider.GetUtcNow();
        try
        {
            policy.ValidateContent(fileName, mediaType, written.Length, written.Prefix.Span);
        }
        catch (FormAttachmentRejectedException rejection)
        {
            await contentStore.DeleteAsync(written.ContentKey, cancellationToken).ConfigureAwait(false);
            var rejected = new FormAttachment(attachmentId, draftId, mutation.Actor.Id, fileName, mediaType, written.Length, written.Sha256, FormAttachmentState.Rejected, now, now, mutation.Actor, rejection.Code);
            return Result(await store.PersistAsync(new FormAttachmentPersistenceCommand("upload-attachment", fingerprint, rejected, null, mutation, true), cancellationToken).ConfigureAwait(false));
        }
        FormAttachmentScanResult verdict;
        try
        {
            await using var scanContent = await contentStore.OpenQuarantinedAsync(written.ContentKey, cancellationToken).ConfigureAwait(false);
            verdict = await scanner.ScanAsync(new FormAttachmentScanRequest(attachmentId, fileName, mediaType, written.Length, written.Sha256, scanContent), cancellationToken).ConfigureAwait(false);
        }
        catch
        {
            await contentStore.DeleteAsync(written.ContentKey, cancellationToken).ConfigureAwait(false);
            throw;
        }
        if (string.IsNullOrWhiteSpace(verdict.Code) || verdict.Code.Length > 128)
        {
            await contentStore.DeleteAsync(written.ContentKey, cancellationToken).ConfigureAwait(false);
            throw new InvalidOperationException("The attachment scanner returned an invalid public-safe code.");
        }
        if (!verdict.IsClean)
        {
            await contentStore.DeleteAsync(written.ContentKey, cancellationToken).ConfigureAwait(false);
            var rejected = new FormAttachment(attachmentId, draftId, mutation.Actor.Id, fileName, mediaType, written.Length, written.Sha256, FormAttachmentState.Rejected, now, now, mutation.Actor, verdict.Code);
            return Result(await store.PersistAsync(new FormAttachmentPersistenceCommand("upload-attachment", fingerprint, rejected, null, mutation, true), cancellationToken).ConfigureAwait(false));
        }
        var availableKey = await contentStore.PromoteAsync(written.ContentKey, cancellationToken).ConfigureAwait(false);
        var available = new FormAttachment(attachmentId, draftId, mutation.Actor.Id, fileName, mediaType, written.Length, written.Sha256, FormAttachmentState.Available, now, now, mutation.Actor);
        return Result(await store.PersistAsync(new FormAttachmentPersistenceCommand("upload-attachment", fingerprint, available, availableKey, mutation, true), cancellationToken).ConfigureAwait(false));
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormAttachment>> ScanAsync(FormAttachmentId attachmentId, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, expected: true);
        var fingerprint = Fingerprint("scan-attachment", attachmentId, mutation);
        var replay = await store.ReplayAsync(attachmentId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return Result(replay);
        var snapshot = await store.GetAsync(attachmentId, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The form attachment does not exist.");
        RequireOwner(snapshot.Attachment.OwnerId, mutation.Actor);
        RequireExpected(mutation, snapshot.Version);
        return await ScanCoreAsync(snapshot, mutation, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public async ValueTask<FormAttachmentDocument?> GetAsync(FormAttachmentId attachmentId, FormRequestContext request, CancellationToken cancellationToken = default)
    {
        ValidateRequest(request);
        var snapshot = await store.GetAsync(attachmentId, cancellationToken).ConfigureAwait(false);
        if (snapshot is null) return null;
        RequireVisible(snapshot.Attachment.OwnerId, request);
        return new FormAttachmentDocument(snapshot.Attachment, snapshot.Version);
    }

    /// <inheritdoc />
    public async ValueTask<FormPage<FormAttachmentDocument>> FindAsync(FormDraftId draftId, FormRequestContext request, int first = 0, int maximum = 100, CancellationToken cancellationToken = default)
    {
        ValidateRequest(request);
        if (first < 0 || maximum is < 1 or > 1000) throw new ArgumentOutOfRangeException(nameof(maximum), "Attachment paging must use a nonnegative offset and 1-1000 items.");
        var draft = await drafts.GetByDraftAsync(draftId, cancellationToken).ConfigureAwait(false);
        if (draft is null) return new FormPage<FormAttachmentDocument>([]);
        RequireVisible(draft.Draft.OwnerId, request);
        var found = new List<FormAttachmentDocument>();
        await foreach (var snapshot in store.FindByDraftAsync(draftId, cancellationToken).ConfigureAwait(false)) found.Add(new FormAttachmentDocument(snapshot.Attachment, snapshot.Version));
        var ordered = found.OrderByDescending(item => item.Attachment.CreatedAt).ThenBy(item => item.Attachment.Id.Value, StringComparer.Ordinal).ToArray();
        return new FormPage<FormAttachmentDocument>(ordered.Skip(first).Take(maximum).ToArray(), ordered.Length);
    }

    /// <inheritdoc />
    public async ValueTask<Stream> OpenReadAsync(FormAttachmentId attachmentId, FormRequestContext request, CancellationToken cancellationToken = default)
    {
        ValidateRequest(request);
        var snapshot = await store.GetAsync(attachmentId, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The form attachment does not exist.");
        RequireVisible(snapshot.Attachment.OwnerId, request);
        if (snapshot.Attachment.State != FormAttachmentState.Available || string.IsNullOrWhiteSpace(snapshot.ContentKey)) throw new InvalidOperationException("The form attachment is not available.");
        return await contentStore.OpenAvailableAsync(snapshot.ContentKey, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormAttachment>> RemoveAsync(FormAttachmentId attachmentId, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, expected: true);
        var fingerprint = Fingerprint("remove-attachment", attachmentId, mutation);
        var replay = await store.ReplayAsync(attachmentId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return Result(replay);
        var snapshot = await store.GetAsync(attachmentId, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The form attachment does not exist.");
        RequireOwner(snapshot.Attachment.OwnerId, mutation.Actor);
        RequireExpected(mutation, snapshot.Version);
        if (snapshot.Attachment.State == FormAttachmentState.Removed) throw new InvalidOperationException("The form attachment is already removed.");
        if (snapshot.ContentKey is not null) await contentStore.DeleteAsync(snapshot.ContentKey, cancellationToken).ConfigureAwait(false);
        var removed = snapshot.Attachment with { State = FormAttachmentState.Removed, UpdatedAt = timeProvider.GetUtcNow(), UpdatedBy = mutation.Actor };
        return Result(await store.PersistAsync(new FormAttachmentPersistenceCommand("remove-attachment", fingerprint, removed, null, mutation), cancellationToken).ConfigureAwait(false));
    }

    /// <summary>Scans a quarantined snapshot and persists promotion or rejection.</summary>
    private async ValueTask<FormMutationResult<FormAttachment>> ScanCoreAsync(FormAttachmentSnapshot snapshot, FormMutationContext mutation, CancellationToken cancellationToken)
    {
        if (snapshot.Attachment.State != FormAttachmentState.PendingScan || string.IsNullOrWhiteSpace(snapshot.ContentKey)) throw new InvalidOperationException("Only a quarantined attachment can be scanned.");
        await using var content = await contentStore.OpenQuarantinedAsync(snapshot.ContentKey, cancellationToken).ConfigureAwait(false);
        var verdict = await scanner.ScanAsync(new FormAttachmentScanRequest(snapshot.Attachment.Id, snapshot.Attachment.FileName, snapshot.Attachment.MediaType, snapshot.Attachment.Length, snapshot.Attachment.Sha256, content), cancellationToken).ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(verdict.Code) || verdict.Code.Length > 128) throw new InvalidOperationException("The attachment scanner returned an invalid public-safe code.");
        var fingerprint = Fingerprint("scan-attachment", snapshot.Attachment.Id, mutation);
        if (!verdict.IsClean)
        {
            await contentStore.DeleteAsync(snapshot.ContentKey, cancellationToken).ConfigureAwait(false);
            var rejected = snapshot.Attachment with { State = FormAttachmentState.Rejected, RejectionCode = verdict.Code, UpdatedAt = timeProvider.GetUtcNow(), UpdatedBy = mutation.Actor };
            return Result(await store.PersistAsync(new FormAttachmentPersistenceCommand("scan-attachment", fingerprint, rejected, null, mutation), cancellationToken).ConfigureAwait(false));
        }
        var availableKey = await contentStore.PromoteAsync(snapshot.ContentKey, cancellationToken).ConfigureAwait(false);
        var available = snapshot.Attachment with { State = FormAttachmentState.Available, RejectionCode = null, UpdatedAt = timeProvider.GetUtcNow(), UpdatedBy = mutation.Actor };
        return Result(await store.PersistAsync(new FormAttachmentPersistenceCommand("scan-attachment", fingerprint, available, availableKey, mutation), cancellationToken).ConfigureAwait(false));
    }

    /// <summary>Projects a storage result to the semantic mutation contract.</summary>
    private static FormMutationResult<FormAttachment> Result(FormAttachmentPersistenceResult result) => new(result.Snapshot.Attachment, result.Snapshot.Version, result.WasReplay);
    /// <summary>Computes a durable fingerprint over operation, payload and mutation context.</summary>
    private static string Fingerprint(string operation, object payload, FormMutationContext mutation) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new { operation, payload, mutation }, SerializerOptions))));
    /// <summary>Requires the mutating actor to own the attachment.</summary>
    private static void RequireOwner(string ownerId, FormAuditActor actor) { if (!string.Equals(ownerId, actor.Id, StringComparison.Ordinal)) throw new UnauthorizedAccessException("The form attachment is not visible to this actor."); }
    /// <summary>Requires ownership unless a trusted adapter supplied administrative reach.</summary>
    private static void RequireVisible(string ownerId, FormRequestContext request) { if (!request.CanAccessAll && !string.Equals(ownerId, request.Actor.Id, StringComparison.Ordinal)) throw new UnauthorizedAccessException("The form attachment is not visible to this actor."); }
    /// <summary>Requires exact opaque optimistic concurrency.</summary>
    private static void RequireExpected(FormMutationContext mutation, FormConcurrencyToken version) { if (!string.Equals(mutation.ExpectedVersion?.Value, version.Value, StringComparison.Ordinal)) throw new InvalidOperationException("The form attachment changed since it was read."); }

    /// <summary>Rejects request contexts without a stable server-derived actor.</summary>
    private static void ValidateRequest(FormRequestContext request)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.Actor.Kind);
    }

    /// <summary>Rejects incomplete mutation evidence or incorrect create/update concurrency shape.</summary>
    private static void ValidateMutation(FormMutationContext mutation, bool expected)
    {
        ArgumentNullException.ThrowIfNull(mutation);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.IdempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Kind);
        if (mutation.RequestedAt == default) throw new ArgumentException("A mutation timestamp is required.", nameof(mutation));
        if (expected != (mutation.ExpectedVersion is not null)) throw new InvalidOperationException(expected ? "An optimistic concurrency version is required." : "A create mutation cannot carry an existing version.");
    }
}
