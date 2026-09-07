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

namespace Orbyss.Forms.Web.Management;

/// <summary>Composes the optional governed form management plane into one selected shell.</summary>
[ShellFeature(name: "Orbyss.Forms.Web.Management", DisplayName = "Orbyss Forms Form Management", Description = "Provides authenticated form authoring, lifecycle, publication, and compatibility endpoints.")]
public sealed class OrbyssFormManagementFeature(ShellSettings settings) : IWebShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) => services.Configure<FormManagementWebOptions>(settings.GetConfigurationRoot().GetSection(FormManagementWebOptions.SectionName));

    /// <inheritdoc />
    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment)
    {
        _ = endpoints.ServiceProvider.GetRequiredService<IFormAuthoring>();
        _ = endpoints.ServiceProvider.GetRequiredService<IFormCatalogQueries>();
        _ = endpoints.ServiceProvider.GetRequiredService<IFormReleaseLifecycle>();
        _ = endpoints.ServiceProvider.GetRequiredService<IFormCompatibilityAnalyzer>();
        var options = endpoints.ServiceProvider.GetRequiredService<IOptions<FormManagementWebOptions>>().Value;
        ValidateOptions(options);
        var group = endpoints.MapGroup(options.RoutePrefix).WithTags("Orbyss Forms Form Management");

        var find = group.MapGet("/forms", async (string? search, int? first, int? maximum, IFormCatalogQueries queries, CancellationToken cancellationToken) => Results.Ok(await queries.FindAsync(search, first ?? 0, maximum ?? 100, cancellationToken).ConfigureAwait(false)));
        Protect(find, options.ReadPolicy);
        var get = group.MapGet("/forms/{formId}", async (string formId, IFormCatalogQueries queries, CancellationToken cancellationToken) => { var value = await queries.GetDefinitionAsync(new FormId(formId), cancellationToken).ConfigureAwait(false); return value is null ? Results.NotFound() : Results.Ok(value); });
        Protect(get, options.ReadPolicy);
        var create = group.MapPost("/forms", async (FormDefinitionWriteRequest request, ClaimsPrincipal user, IFormAuthoring authoring, CancellationToken cancellationToken) => Results.Ok(await authoring.CreateAsync(request.Definition, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(create, options.WritePolicy);
        var replace = group.MapPut("/forms/{formId}", async (string formId, FormDefinitionWriteRequest request, ClaimsPrincipal user, IFormAuthoring authoring, CancellationToken cancellationToken) =>
        {
            if (!string.Equals(formId, request.Definition.Id.Value, StringComparison.Ordinal)) return Results.BadRequest();
            return Results.Ok(await authoring.ReplaceAsync(request.Definition, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false));
        });
        Protect(replace, options.WritePolicy);
        var validate = group.MapPost("/forms/validate", async (FormDefinition definition, IFormAuthoring authoring, CancellationToken cancellationToken) => Results.Ok(await authoring.ValidateAsync(definition, cancellationToken).ConfigureAwait(false)));
        Protect(validate, options.WritePolicy);
        var compile = group.MapPost("/forms/{formId}/{revision:long}/compile", async (string formId, long revision, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken) => Results.Ok(await lifecycle.CompileAsync(new FormId(formId), new FormRevision(revision), cancellationToken).ConfigureAwait(false)));
        Protect(compile, options.WritePolicy);

        var review = group.MapPost("/forms/{formId}/{revision:long}/review", async (string formId, long revision, FormReviewRequest request, ClaimsPrincipal user, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken) => Results.Ok(await lifecycle.SubmitForReviewAsync(new FormId(formId), new FormRevision(revision), request.Evidence, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(review, options.ReviewPolicy);
        var approve = group.MapPost("/forms/{formId}/{revision:long}/approve", async (string formId, long revision, FormWebMutation request, ClaimsPrincipal user, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken) => Results.Ok(await lifecycle.ApproveAsync(new FormId(formId), new FormRevision(revision), Mutation(request, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(approve, options.ReviewPolicy);
        var publish = group.MapPost("/forms/{formId}/{revision:long}/publish", async (string formId, long revision, FormWebMutation request, ClaimsPrincipal user, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken) => Results.Ok(await lifecycle.PublishAsync(new FormId(formId), new FormRevision(revision), Mutation(request, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(publish, options.PublishPolicy);

        var release = group.MapGet("/releases/{releaseId}", async (string releaseId, IFormCatalogQueries queries, CancellationToken cancellationToken) => { var value = await queries.GetReleaseAsync(new FormReleaseId(releaseId), cancellationToken).ConfigureAwait(false); return value is null ? Results.NotFound() : Results.Ok(value); });
        Protect(release, options.ReadPolicy);
        var diff = group.MapGet("/releases/{baselineId}/diff/{candidateId}", async (string baselineId, string candidateId, IFormCatalogQueries queries, IFormCompatibilityAnalyzer analyzer, CancellationToken cancellationToken) =>
        {
            var baseline = await queries.GetReleaseAsync(new FormReleaseId(baselineId), cancellationToken).ConfigureAwait(false);
            var candidate = await queries.GetReleaseAsync(new FormReleaseId(candidateId), cancellationToken).ConfigureAwait(false);
            return baseline is null || candidate is null ? Results.NotFound() : Results.Ok(await analyzer.AnalyzeAsync(baseline, candidate.Candidate, cancellationToken).ConfigureAwait(false));
        });
        Protect(diff, options.ReadPolicy);
        var retire = group.MapPost("/releases/{releaseId}/retire", async (string releaseId, FormWebMutation request, ClaimsPrincipal user, IFormReleaseLifecycle lifecycle, CancellationToken cancellationToken) => Results.Ok(await lifecycle.RetireAsync(new FormReleaseId(releaseId), Mutation(request, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(retire, options.RetirePolicy);
    }

    /// <summary>Builds mutation context from command data and the validated server principal.</summary>
    private static FormMutationContext Mutation(FormWebMutation request, ClaimsPrincipal user, FormManagementWebOptions options)
    {
        if (string.IsNullOrWhiteSpace(request.IdempotencyKey) || request.RequestedAt == default) throw new BadHttpRequestException("A mutation requires an idempotency key and audit timestamp.");
        var subject = user.FindFirst(options.SubjectClaimType)?.Value ?? user.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrWhiteSpace(subject)) throw new BadHttpRequestException("The authenticated principal has no configured subject claim.");
        return new FormMutationContext(request.IdempotencyKey, string.IsNullOrWhiteSpace(request.ExpectedVersion) ? null : new FormConcurrencyToken(request.ExpectedVersion), new FormAuditActor(subject, user.FindFirst(options.ActorKindClaimType)?.Value ?? "user", user.FindFirst(options.DisplayNameClaimType)?.Value ?? user.Identity?.Name), request.RequestedAt, request.CorrelationId);
    }

    /// <summary>Applies a named authorization policy or the host default policy.</summary>
    private static void Protect(RouteHandlerBuilder endpoint, string? policy) { if (string.IsNullOrWhiteSpace(policy)) endpoint.RequireAuthorization(); else endpoint.RequireAuthorization(policy); }
    /// <summary>Rejects invalid routes or claim mappings at shell startup.</summary>
    private static void ValidateOptions(FormManagementWebOptions options)
    {
        if (options.RoutePrefix.Length is < 2 or > 128 || !options.RoutePrefix.StartsWith("/", StringComparison.Ordinal) || options.RoutePrefix.EndsWith("/", StringComparison.Ordinal) || options.RoutePrefix.Contains("//", StringComparison.Ordinal) || options.RoutePrefix.IndexOfAny(['{', '?', '#']) >= 0) throw new InvalidOperationException("Form management route prefix must be a fixed absolute path without a trailing slash.");
        if (string.IsNullOrWhiteSpace(options.SubjectClaimType) || string.IsNullOrWhiteSpace(options.ActorKindClaimType) || string.IsNullOrWhiteSpace(options.DisplayNameClaimType)) throw new InvalidOperationException("Form management claim mappings are required.");
    }
}
