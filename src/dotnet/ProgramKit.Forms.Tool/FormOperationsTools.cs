using System.ComponentModel;
using System.Security.Claims;
using ModelContextProtocol.Server;

namespace ProgramKit.Forms.Tool;

/// <summary>Exposes owner-scoped form operations without creating a second validation or policy engine.</summary>
[McpServerToolType]
public sealed class FormOperationsTools
{
    /// <summary>Prevents direct construction; the SDK binds the static governed tool methods.</summary>
    private FormOperationsTools() { }
    /// <summary>Creates a resumable draft through the application service.</summary>
    [McpServerTool(Name = "forms.drafts.create", Title = "Create form draft", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Create an owner-scoped resumable draft bound to an exact immutable form release. The idempotency key must be stable for retries.")]
    public static async ValueTask<FormMutationResult<FormDraft>> CreateDraftAsync(string draftId, string releaseId, string json, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormDraftOperations drafts, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await drafts.CreateAsync(new FormDraftId(draftId), new FormReleaseId(releaseId), json, CreateMutation(idempotencyKey, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Reads one owner-visible draft.</summary>
    [McpServerTool(Name = "forms.drafts.get", Title = "Get form draft", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Get one resumable draft visible to the authenticated owner.")]
    public static async ValueTask<FormDraftDocument?> GetDraftAsync(string draftId, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormDraftOperations drafts, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await drafts.GetAsync(new FormDraftId(draftId), new FormRequestContext(actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Lists bounded owner-visible drafts.</summary>
    [McpServerTool(Name = "forms.drafts.list", Title = "List form drafts", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("List a bounded page of resumable drafts owned by the authenticated caller.")]
    public static async ValueTask<FormPage<FormDraftDocument>> ListDraftsAsync(int first, int maximum, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormDraftOperations drafts, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await drafts.FindDraftsAsync(new FormRequestContext(actor), first, maximum, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Saves partial data after application-owned draft validation.</summary>
    [McpServerTool(Name = "forms.drafts.save", Title = "Save form draft", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Save partial JSON data to an active owner-scoped draft using its exact opaque version.")]
    public static async ValueTask<FormMutationResult<FormDraft>> SaveDraftAsync(string draftId, string json, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormDraftOperations drafts, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await drafts.SaveAsync(new FormDraftId(draftId), json, UpdateMutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Abandons a draft without deleting its audit record.</summary>
    [McpServerTool(Name = "forms.drafts.abandon", Title = "Abandon form draft", ReadOnly = false, Destructive = true, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Abandon an active owner-scoped draft using its exact opaque version. This makes it non-editable but preserves audit evidence.")]
    public static async ValueTask<FormMutationResult<FormDraft>> AbandonDraftAsync(string draftId, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormDraftOperations drafts, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await drafts.AbandonAsync(new FormDraftId(draftId), UpdateMutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Migrates an active draft to a newer immutable release.</summary>
    [McpServerTool(Name = "forms.drafts.migrate", Title = "Migrate form draft", ReadOnly = false, Destructive = true, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Migrate an active owner-scoped draft to a newer release. Breaking compatibility requires an explicitly registered trusted migration ID.")]
    public static async ValueTask<FormMutationResult<FormDraft>> MigrateDraftAsync(string draftId, string targetReleaseId, string? migrationId, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormDraftMigrationOperations migrations, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await migrations.MigrateAsync(new FormDraftId(draftId), new FormReleaseId(targetReleaseId), migrationId, UpdateMutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Creates an immutable final submission after authoritative validation.</summary>
    [McpServerTool(Name = "forms.submissions.submit", Title = "Submit form draft", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Authoritatively validate and submit an active draft with explicitly selected clean attachment IDs.")]
    public static async ValueTask<FormMutationResult<FormSubmission>> SubmitDraftAsync(string draftId, string[] attachmentIds, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormSubmissionOperations submissions, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await submissions.SubmitAsync(new FormDraftId(draftId), attachmentIds.Select(id => new FormAttachmentId(id)).ToArray(), UpdateMutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Reads one owner-visible submission.</summary>
    [McpServerTool(Name = "forms.submissions.get", Title = "Get form submission", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Get one immutable form submission visible to the authenticated owner.")]
    public static async ValueTask<FormSubmissionDocument?> GetSubmissionAsync(string submissionId, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormSubmissionOperations submissions, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await submissions.GetAsync(new FormSubmissionId(submissionId), new FormRequestContext(actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Lists bounded owner-visible submissions.</summary>
    [McpServerTool(Name = "forms.submissions.list", Title = "List form submissions", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("List a bounded page of immutable submissions owned by the authenticated caller.")]
    public static async ValueTask<FormPage<FormSubmissionDocument>> ListSubmissionsAsync(int first, int maximum, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormSubmissionOperations submissions, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await submissions.FindSubmissionsAsync(new FormRequestContext(actor), first, maximum, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Withdraws a pending owner submission without deleting its payload.</summary>
    [McpServerTool(Name = "forms.submissions.withdraw", Title = "Withdraw form submission", ReadOnly = false, Destructive = true, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Withdraw a pending owner-scoped submission using its exact opaque version while preserving its immutable payload and audit record.")]
    public static async ValueTask<FormMutationResult<FormSubmission>> WithdrawSubmissionAsync(string submissionId, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormSubmissionOperations submissions, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await submissions.WithdrawAsync(new FormSubmissionId(submissionId), UpdateMutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Lists attachment metadata without exposing content or provider keys.</summary>
    [McpServerTool(Name = "forms.attachments.list", Title = "List form attachments", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("List owner-visible attachment metadata for a draft. Binary content and storage locators are never returned.")]
    public static async ValueTask<FormPage<FormAttachmentDocument>> ListAttachmentsAsync(string draftId, int first, int maximum, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormAttachmentOperations attachments, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await attachments.FindAsync(new FormDraftId(draftId), new FormRequestContext(actor), first, maximum, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Creates a server-timestamped create mutation.</summary>
    private static FormMutationContext CreateMutation(string key, DateTimeOffset requestedAt, FormAuditActor actor) => new(key, null, actor, requestedAt);
    /// <summary>Creates a server-timestamped optimistic update mutation.</summary>
    private static FormMutationContext UpdateMutation(string key, string version, DateTimeOffset requestedAt, FormAuditActor actor) => new(key, new FormConcurrencyToken(version), actor, requestedAt);
}
