using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Orbyss.Forms;

/// <summary>Orchestrates owner-scoped drafts and immutable submissions over replaceable durable stores.</summary>
public sealed class DefaultFormSubmissionService : IFormDraftOperations, IFormDraftMigrationOperations, IFormSubmissionOperations, IFormSubmissionReview
{
    /// <summary>Provides stable web serialization for durable command fingerprints.</summary>
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web);
    /// <summary>Persists draft/submission aggregates and replay history.</summary>
    private readonly IFormSubmissionStore store;
    /// <summary>Provides clean attachment metadata used at submission.</summary>
    private readonly IFormAttachmentStore attachments;
    /// <summary>Resolves immutable form releases.</summary>
    private readonly IFormReleaseStore releases;
    /// <summary>Performs server-authoritative data validation.</summary>
    private readonly IFormDataValidator validator;
    /// <summary>Bounds data size and query work.</summary>
    private readonly FormSubmissionOptions options;
    /// <summary>Supplies server-observed lifecycle timestamps.</summary>
    private readonly TimeProvider timeProvider;
    /// <summary>Analyzes source-to-target release compatibility for draft migration.</summary>
    private readonly IFormCompatibilityAnalyzer? compatibilityAnalyzer;
    /// <summary>Holds explicitly registered trusted draft-data migrations by stable identity.</summary>
    private readonly IReadOnlyDictionary<string, IFormDraftDataMigration> migrations;

    /// <summary>Initializes governed form-data orchestration over explicitly selected stores.</summary>
    public DefaultFormSubmissionService(IFormSubmissionStore store, IFormAttachmentStore attachments, IFormReleaseStore releases, IFormDataValidator validator, FormSubmissionOptions? options = null, TimeProvider? timeProvider = null, IFormCompatibilityAnalyzer? compatibilityAnalyzer = null, IEnumerable<IFormDraftDataMigration>? migrations = null)
    {
        this.store = store ?? throw new ArgumentNullException(nameof(store));
        this.attachments = attachments ?? throw new ArgumentNullException(nameof(attachments));
        this.releases = releases ?? throw new ArgumentNullException(nameof(releases));
        this.validator = validator ?? throw new ArgumentNullException(nameof(validator));
        this.options = options ?? new FormSubmissionOptions();
        if (this.options.MaximumDataBytes is < 2 or > 67_108_864) throw new ArgumentOutOfRangeException(nameof(options), "The form data limit must be between 2 bytes and 64 MiB.");
        if (this.options.MaximumQuerySize is < 1 or > 10_000) throw new ArgumentOutOfRangeException(nameof(options), "The query bound must be between 1 and 10,000.");
        this.timeProvider = timeProvider ?? TimeProvider.System;
        this.compatibilityAnalyzer = compatibilityAnalyzer;
        this.migrations = (migrations ?? []).ToDictionary(item => item.Id, StringComparer.Ordinal);
        if (this.migrations.Keys.Any(id => string.IsNullOrWhiteSpace(id) || id.Length > 128)) throw new ArgumentException("Draft migration identifiers must contain from 1 through 128 characters.", nameof(migrations));
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormDraft>> CreateAsync(FormDraftId draftId, FormReleaseId releaseId, string json, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateId(draftId.Value, nameof(draftId));
        ValidateId(releaseId.Value, nameof(releaseId));
        ValidateMutation(mutation, false);
        var data = FormDataCodec.Create(json, options.MaximumDataBytes);
        var fingerprint = Fingerprint("create-draft", new { draftId, releaseId, data }, mutation);
        var replay = await store.ReplayAsync(draftId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return DraftResult(replay);
        var release = await RequireReleaseAsync(releaseId, cancellationToken).ConfigureAwait(false);
        await RequireValidAsync(release, data, FormDataValidationMode.Draft, cancellationToken).ConfigureAwait(false);
        var now = timeProvider.GetUtcNow();
        var draft = new FormDraft(draftId, releaseId, mutation.Actor.Id, data, FormDraftState.Active, now, now, mutation.Actor);
        return DraftResult(await store.PersistAsync(new FormSubmissionPersistenceCommand("create-draft", fingerprint, draft, null, mutation, true), cancellationToken).ConfigureAwait(false));
    }

    /// <inheritdoc />
    public async ValueTask<FormDraftDocument?> GetAsync(FormDraftId draftId, FormRequestContext request, CancellationToken cancellationToken = default)
    {
        ValidateRequest(request);
        var snapshot = await store.GetByDraftAsync(draftId, cancellationToken).ConfigureAwait(false);
        if (snapshot is null) return null;
        RequireVisible(snapshot.Draft.OwnerId, request);
        return new FormDraftDocument(snapshot.Draft, snapshot.Version);
    }

    /// <inheritdoc />
    public async ValueTask<FormPage<FormDraftDocument>> FindDraftsAsync(FormRequestContext request, int first = 0, int maximum = 100, CancellationToken cancellationToken = default)
    {
        ValidateRequest(request);
        ValidatePage(first, maximum);
        var found = new List<FormDraftDocument>();
        await foreach (var snapshot in store.FindAsync(cancellationToken).ConfigureAwait(false))
        {
            if (request.CanAccessAll || string.Equals(snapshot.Draft.OwnerId, request.Actor.Id, StringComparison.Ordinal)) found.Add(new FormDraftDocument(snapshot.Draft, snapshot.Version));
            if (found.Count > options.MaximumQuerySize) throw new InvalidDataException("The form draft query exceeded its configured storage bound.");
        }
        var ordered = found.OrderByDescending(item => item.Draft.UpdatedAt).ThenBy(item => item.Draft.Id.Value, StringComparer.Ordinal).ToArray();
        return new FormPage<FormDraftDocument>(ordered.Skip(first).Take(maximum).ToArray(), ordered.Length);
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormDraft>> SaveAsync(FormDraftId draftId, string json, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, true);
        var data = FormDataCodec.Create(json, options.MaximumDataBytes);
        var fingerprint = Fingerprint("save-draft", new { draftId, data }, mutation);
        var replay = await store.ReplayAsync(draftId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return DraftResult(replay);
        var current = await RequireDraftAsync(draftId, mutation.Actor, cancellationToken).ConfigureAwait(false);
        RequireExpected(mutation, current.Version);
        if (current.Draft.State != FormDraftState.Active) throw new InvalidOperationException("Only an active draft can be saved.");
        var release = await RequireReleaseAsync(current.Draft.ReleaseId, cancellationToken).ConfigureAwait(false);
        await RequireValidAsync(release, data, FormDataValidationMode.Draft, cancellationToken).ConfigureAwait(false);
        var next = current.Draft with { Data = data, UpdatedAt = timeProvider.GetUtcNow(), UpdatedBy = mutation.Actor };
        return DraftResult(await store.PersistAsync(new FormSubmissionPersistenceCommand("save-draft", fingerprint, next, current.Submission, mutation), cancellationToken).ConfigureAwait(false));
    }

    /// <inheritdoc />
    public ValueTask<FormMutationResult<FormDraft>> AbandonAsync(FormDraftId draftId, FormMutationContext mutation, CancellationToken cancellationToken = default) =>
        ChangeDraftStateAsync(draftId, FormDraftState.Abandoned, "abandon-draft", mutation, cancellationToken);

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormDraft>> MigrateAsync(FormDraftId draftId, FormReleaseId targetReleaseId, string? migrationId, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, true);
        ValidateId(targetReleaseId.Value, nameof(targetReleaseId));
        var normalizedMigrationId = string.IsNullOrWhiteSpace(migrationId) ? null : migrationId.Trim();
        var fingerprint = Fingerprint("migrate-draft", new { draftId, targetReleaseId, migrationId = normalizedMigrationId }, mutation);
        var replay = await store.ReplayAsync(draftId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return DraftResult(replay);
        var current = await RequireDraftAsync(draftId, mutation.Actor, cancellationToken).ConfigureAwait(false);
        RequireExpected(mutation, current.Version);
        if (current.Draft.State != FormDraftState.Active || current.Submission is not null) throw new InvalidOperationException("Only an active unsubmitted draft can be migrated.");
        var source = await releases.GetAsync(current.Draft.ReleaseId, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The draft source release does not exist.");
        var target = await RequireReleaseAsync(targetReleaseId, cancellationToken).ConfigureAwait(false);
        if (source.Candidate.FormId != target.Candidate.FormId || target.Candidate.Revision.Value <= source.Candidate.Revision.Value) throw new InvalidOperationException("A draft migration target must be a newer release of the same form.");
        var analyzer = compatibilityAnalyzer ?? throw new InvalidOperationException("Draft migration requires a registered form compatibility analyzer.");
        var compatibility = await analyzer.AnalyzeAsync(source, target.Candidate, cancellationToken).ConfigureAwait(false);
        FormDataDocument data;
        if (normalizedMigrationId is null)
        {
            if (compatibility.RequiresMigration) throw new InvalidOperationException("A breaking form release requires an explicit trusted draft migration.");
            data = current.Draft.Data;
        }
        else
        {
            if (!migrations.TryGetValue(normalizedMigrationId, out var handler)) throw new InvalidOperationException("The requested draft migration is not registered.");
            data = FormDataCodec.Create(await handler.MigrateAsync(source, target, current.Draft.Data, cancellationToken).ConfigureAwait(false), options.MaximumDataBytes);
        }
        await RequireValidAsync(target, data, FormDataValidationMode.Draft, cancellationToken).ConfigureAwait(false);
        var next = current.Draft with { ReleaseId = target.Id, Data = data, UpdatedAt = timeProvider.GetUtcNow(), UpdatedBy = mutation.Actor };
        return DraftResult(await store.PersistAsync(new FormSubmissionPersistenceCommand("migrate-draft", fingerprint, next, null, mutation), cancellationToken).ConfigureAwait(false));
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormSubmission>> SubmitAsync(FormDraftId draftId, IReadOnlyList<FormAttachmentId> attachmentIds, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(attachmentIds);
        ValidateMutation(mutation, true);
        if (attachmentIds.Count > 100 || attachmentIds.Distinct().Count() != attachmentIds.Count) throw new InvalidOperationException("A submission may reference at most 100 unique attachments.");
        var fingerprint = Fingerprint("submit-draft", new { draftId, attachmentIds }, mutation);
        var replay = await store.ReplayAsync(draftId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return SubmissionResult(replay);
        var current = await RequireDraftAsync(draftId, mutation.Actor, cancellationToken).ConfigureAwait(false);
        RequireExpected(mutation, current.Version);
        if (current.Draft.State != FormDraftState.Active || current.Submission is not null) throw new InvalidOperationException("Only an active, unsubmitted draft can be submitted.");
        var release = await RequireReleaseAsync(current.Draft.ReleaseId, cancellationToken).ConfigureAwait(false);
        await RequireValidAsync(release, current.Draft.Data, FormDataValidationMode.Submission, cancellationToken).ConfigureAwait(false);
        foreach (var attachmentId in attachmentIds)
        {
            var attachment = await attachments.GetAsync(attachmentId, cancellationToken).ConfigureAwait(false) ?? throw new InvalidOperationException("A selected attachment does not exist.");
            if (attachment.Attachment.DraftId != draftId || !string.Equals(attachment.Attachment.OwnerId, current.Draft.OwnerId, StringComparison.Ordinal) || attachment.Attachment.State != FormAttachmentState.Available) throw new InvalidOperationException("Every selected attachment must be clean, available, and owned by this draft.");
        }
        var now = timeProvider.GetUtcNow();
        var submission = new FormSubmission(SubmissionId(draftId), draftId, current.Draft.ReleaseId, current.Draft.OwnerId, current.Draft.Data, attachmentIds.ToArray(), FormSubmissionState.Submitted, now, mutation.Actor, now, mutation.Actor);
        var draft = current.Draft with { State = FormDraftState.Submitted, UpdatedAt = now, UpdatedBy = mutation.Actor };
        return SubmissionResult(await store.PersistAsync(new FormSubmissionPersistenceCommand("submit-draft", fingerprint, draft, submission, mutation), cancellationToken).ConfigureAwait(false));
    }

    /// <inheritdoc />
    public async ValueTask<FormSubmissionDocument?> GetAsync(FormSubmissionId submissionId, FormRequestContext request, CancellationToken cancellationToken = default)
    {
        ValidateRequest(request);
        var snapshot = await store.GetBySubmissionAsync(submissionId, cancellationToken).ConfigureAwait(false);
        if (snapshot?.Submission is null) return null;
        RequireVisible(snapshot.Submission.OwnerId, request);
        return new FormSubmissionDocument(snapshot.Submission, snapshot.Version);
    }

    /// <inheritdoc />
    public async ValueTask<FormPage<FormSubmissionDocument>> FindSubmissionsAsync(FormRequestContext request, int first = 0, int maximum = 100, CancellationToken cancellationToken = default)
    {
        ValidateRequest(request);
        ValidatePage(first, maximum);
        var found = new List<FormSubmissionDocument>();
        await foreach (var snapshot in store.FindAsync(cancellationToken).ConfigureAwait(false))
        {
            if (snapshot.Submission is { } submission && (request.CanAccessAll || string.Equals(submission.OwnerId, request.Actor.Id, StringComparison.Ordinal))) found.Add(new FormSubmissionDocument(submission, snapshot.Version));
            if (found.Count > options.MaximumQuerySize) throw new InvalidDataException("The form submission query exceeded its configured storage bound.");
        }
        var ordered = found.OrderByDescending(item => item.Submission.SubmittedAt).ThenBy(item => item.Submission.Id.Value, StringComparer.Ordinal).ToArray();
        return new FormPage<FormSubmissionDocument>(ordered.Skip(first).Take(maximum).ToArray(), ordered.Length);
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormSubmission>> WithdrawAsync(FormSubmissionId submissionId, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, true);
        var current = await store.GetBySubmissionAsync(submissionId, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The form submission does not exist.");
        var fingerprint = Fingerprint("withdraw-submission", submissionId, mutation);
        var replay = await store.ReplayAsync(current.Draft.Id, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return SubmissionResult(replay);
        if (current.Submission is null || !string.Equals(current.Submission.OwnerId, mutation.Actor.Id, StringComparison.Ordinal)) throw new UnauthorizedAccessException("The form submission is not visible to this actor.");
        RequireExpected(mutation, current.Version);
        if (current.Submission.State != FormSubmissionState.Submitted) throw new InvalidOperationException("Only a pending submission can be withdrawn.");
        var next = current.Submission with { State = FormSubmissionState.Withdrawn, UpdatedAt = timeProvider.GetUtcNow(), UpdatedBy = mutation.Actor };
        return SubmissionResult(await store.PersistAsync(new FormSubmissionPersistenceCommand("withdraw-submission", fingerprint, current.Draft, next, mutation), cancellationToken).ConfigureAwait(false));
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormSubmission>> DecideAsync(FormSubmissionId submissionId, bool accept, string? reason, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, true);
        if (reason?.Length > 2000) throw new ArgumentOutOfRangeException(nameof(reason), "A decision reason cannot exceed 2,000 characters.");
        var current = await store.GetBySubmissionAsync(submissionId, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The form submission does not exist.");
        var fingerprint = Fingerprint(accept ? "accept-submission" : "reject-submission", new { submissionId, reason }, mutation);
        var replay = await store.ReplayAsync(current.Draft.Id, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return SubmissionResult(replay);
        RequireExpected(mutation, current.Version);
        if (current.Submission is null || current.Submission.State != FormSubmissionState.Submitted) throw new InvalidOperationException("Only a pending submission can receive a decision.");
        var next = current.Submission with { State = accept ? FormSubmissionState.Accepted : FormSubmissionState.Rejected, DecisionReason = reason?.Trim(), UpdatedAt = timeProvider.GetUtcNow(), UpdatedBy = mutation.Actor };
        return SubmissionResult(await store.PersistAsync(new FormSubmissionPersistenceCommand(accept ? "accept-submission" : "reject-submission", fingerprint, current.Draft, next, mutation), cancellationToken).ConfigureAwait(false));
    }

    /// <summary>Applies an owner-scoped optimistic draft state transition.</summary>
    private async ValueTask<FormMutationResult<FormDraft>> ChangeDraftStateAsync(FormDraftId draftId, FormDraftState state, string operation, FormMutationContext mutation, CancellationToken cancellationToken)
    {
        ValidateMutation(mutation, true);
        var fingerprint = Fingerprint(operation, draftId, mutation);
        var replay = await store.ReplayAsync(draftId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return DraftResult(replay);
        var current = await RequireDraftAsync(draftId, mutation.Actor, cancellationToken).ConfigureAwait(false);
        RequireExpected(mutation, current.Version);
        if (current.Draft.State != FormDraftState.Active) throw new InvalidOperationException("Only an active draft can change to this state.");
        var next = current.Draft with { State = state, UpdatedAt = timeProvider.GetUtcNow(), UpdatedBy = mutation.Actor };
        return DraftResult(await store.PersistAsync(new FormSubmissionPersistenceCommand(operation, fingerprint, next, current.Submission, mutation), cancellationToken).ConfigureAwait(false));
    }

    /// <summary>Loads one draft and requires exact owner identity.</summary>
    private async ValueTask<FormSubmissionAggregateSnapshot> RequireDraftAsync(FormDraftId id, FormAuditActor actor, CancellationToken cancellationToken)
    {
        var snapshot = await store.GetByDraftAsync(id, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The form draft does not exist.");
        if (!string.Equals(snapshot.Draft.OwnerId, actor.Id, StringComparison.Ordinal)) throw new UnauthorizedAccessException("The form draft is not visible to this actor.");
        return snapshot;
    }

    /// <summary>Loads one active immutable form release.</summary>
    private async ValueTask<FormRelease> RequireReleaseAsync(FormReleaseId id, CancellationToken cancellationToken)
    {
        var release = await releases.GetAsync(id, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The immutable form release does not exist.");
        if (release.Retired) throw new InvalidOperationException("A retired form release cannot accept new data.");
        return release;
    }

    /// <summary>Converts blocking authoritative diagnostics to one stable validation failure.</summary>
    private async ValueTask RequireValidAsync(FormRelease release, FormDataDocument data, FormDataValidationMode mode, CancellationToken cancellationToken)
    {
        var diagnostics = await validator.ValidateAsync(release, data, mode, cancellationToken).ConfigureAwait(false);
        if (diagnostics.Any(item => item.Severity == FormDiagnosticSeverity.Error)) throw new FormDataValidationException(diagnostics);
    }

    /// <summary>Projects persisted aggregate state to a draft mutation result.</summary>
    private static FormMutationResult<FormDraft> DraftResult(FormSubmissionPersistenceResult result) => new(result.Snapshot.Draft, result.Snapshot.Version, result.WasReplay);
    /// <summary>Projects persisted aggregate state to a submission mutation result.</summary>
    private static FormMutationResult<FormSubmission> SubmissionResult(FormSubmissionPersistenceResult result) => new(result.Snapshot.Submission ?? throw new InvalidDataException("The durable command replay has no submission."), result.Snapshot.Version, result.WasReplay);
    /// <summary>Derives a stable one-submission-per-draft identifier without exposing source text.</summary>
    private static FormSubmissionId SubmissionId(FormDraftId draftId) => new("submission-" + Hash(draftId.Value)[..32]);
    /// <summary>Computes a durable command fingerprint.</summary>
    private static string Fingerprint(string operation, object payload, FormMutationContext mutation) => Hash(JsonSerializer.Serialize(new { operation, payload, mutation }, SerializerOptions));
    /// <summary>Computes a lowercase SHA-256 digest.</summary>
    private static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    /// <summary>Rejects incomplete mutation evidence or incorrect create/update concurrency shape.</summary>
    private static void ValidateMutation(FormMutationContext mutation, bool expected)
    {
        ArgumentNullException.ThrowIfNull(mutation);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.IdempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Kind);
        if (mutation.RequestedAt == default) throw new ArgumentException("A mutation timestamp is required.", nameof(mutation));
        if (expected && mutation.ExpectedVersion is null) throw new InvalidOperationException("An optimistic concurrency version is required.");
        if (!expected && mutation.ExpectedVersion is not null) throw new InvalidOperationException("A create mutation cannot carry an existing version.");
    }

    /// <summary>Rejects request contexts without a stable server-derived actor.</summary>
    private static void ValidateRequest(FormRequestContext request)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(request.Actor.Kind);
    }

    /// <summary>Requires ownership unless a trusted adapter supplied administrative reach.</summary>
    private static void RequireVisible(string ownerId, FormRequestContext request)
    {
        if (!request.CanAccessAll && !string.Equals(ownerId, request.Actor.Id, StringComparison.Ordinal)) throw new UnauthorizedAccessException("The form operation is not visible to this actor.");
    }

    /// <summary>Requires exact opaque optimistic concurrency.</summary>
    private static void RequireExpected(FormMutationContext mutation, FormConcurrencyToken actual)
    {
        if (!string.Equals(mutation.ExpectedVersion?.Value, actual.Value, StringComparison.Ordinal)) throw new InvalidOperationException("The form operation changed since it was read.");
    }

    /// <summary>Applies configured nonnegative and bounded page limits.</summary>
    private void ValidatePage(int first, int maximum)
    {
        if (first < 0) throw new ArgumentOutOfRangeException(nameof(first));
        if (maximum is < 1 || maximum > options.MaximumQuerySize) throw new ArgumentOutOfRangeException(nameof(maximum));
    }

    /// <summary>Requires a bounded portable identifier safe for logs and adapters.</summary>
    private static void ValidateId(string value, string parameter)
    {
        if (string.IsNullOrWhiteSpace(value) || value.Length > 128 || value.Any(character => !char.IsAsciiLetterOrDigit(character) && character is not '-' and not '_' and not '.')) throw new ArgumentException("Identifiers must contain 1-128 ASCII letters, digits, dots, dashes, or underscores.", parameter);
    }
}
