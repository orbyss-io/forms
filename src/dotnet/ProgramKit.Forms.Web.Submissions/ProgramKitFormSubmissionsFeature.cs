using System.Globalization;
using System.Security.Claims;
using CShells;
using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace ProgramKit.Forms.Web.Submissions;

/// <summary>Composes optional form data collection into one selected shell without Host behavior.</summary>
[ShellFeature(name: "ProgramKit.Forms.Web.Submissions", DisplayName = "Program Kit Form Submissions", Description = "Provides authenticated owner-scoped draft, submission, review, and attachment endpoints.")]
public sealed class ProgramKitFormSubmissionsFeature(ShellSettings settings) : IWebShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) => services.Configure<FormSubmissionsWebOptions>(settings.GetConfigurationRoot().GetSection(FormSubmissionsWebOptions.SectionName));

    /// <inheritdoc />
    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment)
    {
        _ = endpoints.ServiceProvider.GetRequiredService<IFormDraftOperations>();
        _ = endpoints.ServiceProvider.GetRequiredService<IFormDraftMigrationOperations>();
        _ = endpoints.ServiceProvider.GetRequiredService<IFormSubmissionOperations>();
        _ = endpoints.ServiceProvider.GetRequiredService<IFormSubmissionReview>();
        _ = endpoints.ServiceProvider.GetRequiredService<IFormAttachmentOperations>();
        var options = endpoints.ServiceProvider.GetRequiredService<IOptions<FormSubmissionsWebOptions>>().Value;
        ValidateOptions(options);
        var group = endpoints.MapGroup(options.RoutePrefix).WithTags("Program Kit Form Submissions");

        var listDrafts = group.MapGet("/drafts", async (int? first, int? maximum, ClaimsPrincipal user, IFormDraftOperations drafts, CancellationToken cancellationToken) => Results.Ok(await drafts.FindDraftsAsync(Request(user, options), first ?? 0, maximum ?? 100, cancellationToken).ConfigureAwait(false)));
        Protect(listDrafts, options.ReadPolicy);
        var getDraft = group.MapGet("/drafts/{draftId}", async (string draftId, ClaimsPrincipal user, IFormDraftOperations drafts, CancellationToken cancellationToken) =>
        {
            var draft = await drafts.GetAsync(new FormDraftId(draftId), Request(user, options), cancellationToken).ConfigureAwait(false);
            return draft is null ? Results.NotFound() : Results.Ok(draft);
        });
        Protect(getDraft, options.ReadPolicy);
        var createDraft = group.MapPost("/drafts", async (CreateFormDraftRequest request, ClaimsPrincipal user, IFormDraftOperations drafts, CancellationToken cancellationToken) => Results.Ok(await drafts.CreateAsync(new FormDraftId(request.DraftId), new FormReleaseId(request.ReleaseId), request.Json, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(createDraft, options.WritePolicy);
        var saveDraft = group.MapPut("/drafts/{draftId}", async (string draftId, SaveFormDraftRequest request, ClaimsPrincipal user, IFormDraftOperations drafts, CancellationToken cancellationToken) => Results.Ok(await drafts.SaveAsync(new FormDraftId(draftId), request.Json, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(saveDraft, options.WritePolicy);
        var abandonDraft = group.MapPost("/drafts/{draftId}/abandon", async (string draftId, FormWebMutation request, ClaimsPrincipal user, IFormDraftOperations drafts, CancellationToken cancellationToken) => Results.Ok(await drafts.AbandonAsync(new FormDraftId(draftId), Mutation(request, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(abandonDraft, options.WritePolicy);
        var migrateDraft = group.MapPost("/drafts/{draftId}/migrate", async (string draftId, MigrateFormDraftRequest request, ClaimsPrincipal user, IFormDraftMigrationOperations migrations, CancellationToken cancellationToken) => Results.Ok(await migrations.MigrateAsync(new FormDraftId(draftId), new FormReleaseId(request.TargetReleaseId), request.MigrationId, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(migrateDraft, options.WritePolicy);

        var submit = group.MapPost("/drafts/{draftId}/submit", async (string draftId, SubmitFormDraftRequest request, ClaimsPrincipal user, IFormSubmissionOperations submissions, CancellationToken cancellationToken) => Results.Ok(await submissions.SubmitAsync(new FormDraftId(draftId), request.AttachmentIds.Select(id => new FormAttachmentId(id)).ToArray(), Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(submit, options.WritePolicy);
        var listSubmissions = group.MapGet("/submissions", async (int? first, int? maximum, ClaimsPrincipal user, IFormSubmissionOperations submissions, CancellationToken cancellationToken) => Results.Ok(await submissions.FindSubmissionsAsync(Request(user, options), first ?? 0, maximum ?? 100, cancellationToken).ConfigureAwait(false)));
        Protect(listSubmissions, options.ReadPolicy);
        var getSubmission = group.MapGet("/submissions/{submissionId}", async (string submissionId, ClaimsPrincipal user, IFormSubmissionOperations submissions, CancellationToken cancellationToken) =>
        {
            var submission = await submissions.GetAsync(new FormSubmissionId(submissionId), Request(user, options), cancellationToken).ConfigureAwait(false);
            return submission is null ? Results.NotFound() : Results.Ok(submission);
        });
        Protect(getSubmission, options.ReadPolicy);
        var withdraw = group.MapPost("/submissions/{submissionId}/withdraw", async (string submissionId, FormWebMutation request, ClaimsPrincipal user, IFormSubmissionOperations submissions, CancellationToken cancellationToken) => Results.Ok(await submissions.WithdrawAsync(new FormSubmissionId(submissionId), Mutation(request, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(withdraw, options.WritePolicy);
        var decide = group.MapPost("/submissions/{submissionId}/decision", async (string submissionId, FormSubmissionDecisionRequest request, ClaimsPrincipal user, IFormSubmissionReview review, CancellationToken cancellationToken) => Results.Ok(await review.DecideAsync(new FormSubmissionId(submissionId), request.Accept, request.Reason, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(decide, options.ReviewPolicy);

        var listAttachments = group.MapGet("/drafts/{draftId}/attachments", async (string draftId, int? first, int? maximum, ClaimsPrincipal user, IFormAttachmentOperations attachments, CancellationToken cancellationToken) => Results.Ok(await attachments.FindAsync(new FormDraftId(draftId), Request(user, options), first ?? 0, maximum ?? 100, cancellationToken).ConfigureAwait(false)));
        Protect(listAttachments, options.ReadPolicy);
        var upload = group.MapPost("/drafts/{draftId}/attachments/{attachmentId}", async (string draftId, string attachmentId, string fileName, HttpRequest request, ClaimsPrincipal user, IFormAttachmentOperations attachments, CancellationToken cancellationToken) =>
        {
            var mediaType = request.ContentType ?? throw new BadHttpRequestException("An attachment Content-Type is required.");
            return Results.Ok(await attachments.UploadAsync(new FormAttachmentId(attachmentId), new FormDraftId(draftId), fileName, mediaType, request.Body, HeaderMutation(request, user, options, expected: false), cancellationToken).ConfigureAwait(false));
        });
        Protect(upload, options.WritePolicy);
        var download = group.MapGet("/attachments/{attachmentId}/content", async (string attachmentId, ClaimsPrincipal user, HttpResponse response, IFormAttachmentOperations attachments, CancellationToken cancellationToken) =>
        {
            var id = new FormAttachmentId(attachmentId);
            var visible = await attachments.GetAsync(id, Request(user, options), cancellationToken).ConfigureAwait(false);
            if (visible is null) return Results.NotFound();
            var stream = await attachments.OpenReadAsync(id, Request(user, options), cancellationToken).ConfigureAwait(false);
            response.Headers.XContentTypeOptions = "nosniff";
            response.Headers.CacheControl = "private, no-store";
            return Results.Stream(stream, visible.Attachment.MediaType, visible.Attachment.FileName, enableRangeProcessing: false);
        });
        Protect(download, options.ReadPolicy);
        var scan = group.MapPost("/attachments/{attachmentId}/scan", async (string attachmentId, FormWebMutation request, ClaimsPrincipal user, IFormAttachmentOperations attachments, CancellationToken cancellationToken) => Results.Ok(await attachments.ScanAsync(new FormAttachmentId(attachmentId), Mutation(request, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(scan, options.ScanPolicy);
        var remove = group.MapPost("/attachments/{attachmentId}/remove", async (string attachmentId, FormWebMutation request, ClaimsPrincipal user, IFormAttachmentOperations attachments, CancellationToken cancellationToken) => Results.Ok(await attachments.RemoveAsync(new FormAttachmentId(attachmentId), Mutation(request, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(remove, options.WritePolicy);
    }

    /// <summary>Builds an owner-only access context from authenticated claims.</summary>
    private static FormRequestContext Request(ClaimsPrincipal user, FormSubmissionsWebOptions options) => new(Actor(user, options));
    /// <summary>Builds audited mutation context while keeping identity out of client payloads.</summary>
    private static FormMutationContext Mutation(FormWebMutation mutation, ClaimsPrincipal user, FormSubmissionsWebOptions options) => new(mutation.IdempotencyKey, string.IsNullOrWhiteSpace(mutation.ExpectedVersion) ? null : new FormConcurrencyToken(mutation.ExpectedVersion), Actor(user, options), mutation.RequestedAt, mutation.CorrelationId);
    /// <summary>Builds streamed-upload mutation metadata from bounded request headers.</summary>
    private static FormMutationContext HeaderMutation(HttpRequest request, ClaimsPrincipal user, FormSubmissionsWebOptions options, bool expected)
    {
        var key = request.Headers["Idempotency-Key"].ToString();
        var version = request.Headers.IfMatch.ToString().Trim('"');
        var requested = request.Headers["X-Requested-At"].ToString();
        if (string.IsNullOrWhiteSpace(key) || !DateTimeOffset.TryParse(requested, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var timestamp)) throw new BadHttpRequestException("Upload headers require Idempotency-Key and an ISO 8601 X-Requested-At value.");
        if (expected && string.IsNullOrWhiteSpace(version)) throw new BadHttpRequestException("An If-Match version is required.");
        return new FormMutationContext(key, string.IsNullOrWhiteSpace(version) ? null : new FormConcurrencyToken(version), Actor(user, options), timestamp, request.Headers["X-Correlation-Id"].ToString());
    }
    /// <summary>Derives a stable audit actor from configured principal claims.</summary>
    private static FormAuditActor Actor(ClaimsPrincipal user, FormSubmissionsWebOptions options)
    {
        var subject = user.FindFirst(options.SubjectClaimType)?.Value ?? user.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrWhiteSpace(subject)) throw new BadHttpRequestException("The authenticated principal has no configured subject claim.");
        return new FormAuditActor(subject, user.FindFirst(options.ActorKindClaimType)?.Value ?? "user", user.FindFirst(options.DisplayNameClaimType)?.Value ?? user.Identity?.Name);
    }
    /// <summary>Applies a named policy or the consumer's default authenticated policy.</summary>
    private static void Protect(RouteHandlerBuilder endpoint, string? policy) { if (string.IsNullOrWhiteSpace(policy)) endpoint.RequireAuthorization(); else endpoint.RequireAuthorization(policy); }
    /// <summary>Rejects unsafe route and claim configuration at shell startup.</summary>
    private static void ValidateOptions(FormSubmissionsWebOptions options)
    {
        if (options.RoutePrefix.Length is < 2 or > 128 || !options.RoutePrefix.StartsWith("/", StringComparison.Ordinal) || options.RoutePrefix.EndsWith("/", StringComparison.Ordinal) || options.RoutePrefix.Contains("//", StringComparison.Ordinal) || options.RoutePrefix.IndexOfAny(['{', '?', '#']) >= 0) throw new InvalidOperationException("The form submissions route prefix must be a fixed absolute path without a trailing slash.");
        if (string.IsNullOrWhiteSpace(options.ReviewPolicy) || string.IsNullOrWhiteSpace(options.SubjectClaimType) || string.IsNullOrWhiteSpace(options.ActorKindClaimType) || string.IsNullOrWhiteSpace(options.DisplayNameClaimType)) throw new InvalidOperationException("Form submission policy and claim mappings are required.");
    }
}
