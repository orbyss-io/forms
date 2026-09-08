using System.ComponentModel;
using System.Security.Claims;
using ModelContextProtocol.Server;

namespace Orbyss.Forms.Management.Tool;

/// <summary>Exposes governed form management without duplicating application lifecycle rules.</summary>
[McpServerToolType]
public sealed class FormManagementTools
{
    /// <summary>Prevents direct construction; the SDK binds static tool methods.</summary>
    private FormManagementTools() { }

    /// <summary>Lists bounded form catalog projections.</summary>
    [McpServerTool(Name = "forms.management.list", Title = "List managed forms", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("List a bounded page of managed form definitions by identifier or name.")]
    public static ValueTask<FormPage<FormCatalogItem>> ListAsync(string? search, int first, int maximum, IFormCatalogQueries queries, CancellationToken cancellationToken) => queries.FindAsync(search, first, maximum, cancellationToken);

    /// <summary>Gets one editable definition with its opaque version.</summary>
    [McpServerTool(Name = "forms.management.get", Title = "Get managed form", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Get one editable provider-neutral form definition and its current opaque version.")]
    public static ValueTask<FormDefinitionDocument?> GetAsync(string formId, IFormCatalogQueries queries, CancellationToken cancellationToken) => queries.GetDefinitionAsync(new FormId(formId), cancellationToken);

    /// <summary>Validates a definition without changing stored state.</summary>
    [McpServerTool(Name = "forms.management.validate", Title = "Validate form", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Validate a complete provider-neutral form definition and return stable diagnostics without storing it.")]
    public static ValueTask<IReadOnlyList<FormDiagnostic>> ValidateAsync(FormDefinition definition, IFormAuthoring authoring, CancellationToken cancellationToken) => authoring.ValidateAsync(definition, cancellationToken);

    /// <summary>Compiles a stored revision without mutating it.</summary>
    [McpServerTool(Name = "forms.management.compile", Title = "Compile form", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Compile the current stored form revision to deterministic JSON Schema, UI Schema, and requirement manifests.")]
    public static ValueTask<FormCandidate> CompileAsync(string formId, long revision, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken) => lifecycle.CompileAsync(new FormId(formId), new FormRevision(revision), cancellationToken);

    /// <summary>Creates a governed form draft.</summary>
    [McpServerTool(Name = "forms.management.create", Title = "Create form", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Create revision 1 of a provider-neutral form draft with durable idempotency and principal-derived audit identity.")]
    public static async ValueTask<FormMutationResult<FormDefinition>> CreateAsync(FormDefinition definition, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormAuthoring authoring, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await authoring.CreateAsync(definition, new FormMutationContext(idempotencyKey, null, actor, requestedAt), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Replaces one editable definition.</summary>
    [McpServerTool(Name = "forms.management.replace", Title = "Replace form", ReadOnly = false, Destructive = true, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Replace an editable definition with the next draft revision using its exact opaque version.")]
    public static async ValueTask<FormMutationResult<FormDefinition>> ReplaceAsync(FormDefinition definition, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormAuthoring authoring, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await authoring.ReplaceAsync(definition, Mutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Submits a compiled revision and its evidence for review.</summary>
    [McpServerTool(Name = "forms.management.submit_review", Title = "Submit form for review", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Compile a draft, bind explicit acceptance-evidence references, and submit the exact revision for review.")]
    public static async ValueTask<FormMutationResult<FormLifecycleState>> SubmitReviewAsync(string formId, long revision, string[] evidence, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await lifecycle.SubmitForReviewAsync(new FormId(formId), new FormRevision(revision), evidence, Mutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Approves an exact reviewed revision.</summary>
    [McpServerTool(Name = "forms.management.approve", Title = "Approve form", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Approve an exact reviewed form revision without publishing it.")]
    public static async ValueTask<FormMutationResult<FormLifecycleState>> ApproveAsync(string formId, long revision, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await lifecycle.ApproveAsync(new FormId(formId), new FormRevision(revision), Mutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Publishes an approved revision as an immutable release.</summary>
    [McpServerTool(Name = "forms.management.publish", Title = "Publish form", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Publish an exact approved form revision as immutable runtime artifacts.")]
    public static async ValueTask<FormMutationResult<FormRelease>> PublishAsync(string formId, long revision, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await lifecycle.PublishAsync(new FormId(formId), new FormRevision(revision), Mutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Gets one immutable release, including retirement state.</summary>
    [McpServerTool(Name = "forms.management.release_get", Title = "Get form release", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Get one immutable form release by its stable identifier.")]
    public static ValueTask<FormRelease?> GetReleaseAsync(string releaseId, IFormCatalogQueries queries, CancellationToken cancellationToken) => queries.GetReleaseAsync(new FormReleaseId(releaseId), cancellationToken);

    /// <summary>Compares a candidate release to its baseline.</summary>
    [McpServerTool(Name = "forms.management.release_compare", Title = "Compare form releases", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Compare two immutable releases and report provider-neutral compatibility impact.")]
    public static async ValueTask<FormCompatibilityReport?> CompareReleasesAsync(string baselineReleaseId, string candidateReleaseId, IFormCatalogQueries queries, IFormCompatibilityAnalyzer analyzer, CancellationToken cancellationToken)
    {
        var baseline = await queries.GetReleaseAsync(new FormReleaseId(baselineReleaseId), cancellationToken).ConfigureAwait(false);
        var candidate = await queries.GetReleaseAsync(new FormReleaseId(candidateReleaseId), cancellationToken).ConfigureAwait(false);
        return baseline is null || candidate is null ? null : await analyzer.AnalyzeAsync(baseline, candidate.Candidate, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Retires a release without deleting its immutable artifacts.</summary>
    [McpServerTool(Name = "forms.management.retire", Title = "Retire form release", ReadOnly = false, Destructive = true, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Retire an immutable form release while preserving its artifacts and audit evidence.")]
    public static async ValueTask<FormMutationResult<FormRelease>> RetireAsync(string releaseId, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, IFormToolActorProvider actors, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await lifecycle.RetireAsync(new FormReleaseId(releaseId), Mutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Creates an optimistic mutation with principal-derived identity.</summary>
    private static FormMutationContext Mutation(string key, string version, DateTimeOffset requestedAt, FormAuditActor actor) => new(key, new FormConcurrencyToken(version), actor, requestedAt);
}
