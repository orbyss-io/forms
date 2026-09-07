using System.Security.Claims;
using CShells;
using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace Orbyss.Localization.Web.Management;

/// <summary>Composes the optional governed localization management plane into one selected shell.</summary>
[ShellFeature(
    name: "Orbyss.Localization.Web.Management",
    DisplayName = "Orbyss Forms Localization Management",
    Description = "Provides authenticated catalog, import, export, lifecycle, and release-diff endpoints.")]
public sealed class OrbyssLocalizationManagementFeature(ShellSettings settings) : IWebShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) =>
        services.Configure<LocalizationManagementWebOptions>(settings.GetConfigurationRoot().GetSection(LocalizationManagementWebOptions.SectionName));

    /// <inheritdoc />
    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment)
    {
        _ = endpoints.ServiceProvider.GetRequiredService<ILocalizationCatalogManagement>();
        _ = endpoints.ServiceProvider.GetRequiredService<ILocalizationCatalogQueries>();
        _ = endpoints.ServiceProvider.GetRequiredService<ILocalizationReleaseLifecycle>();
        _ = endpoints.ServiceProvider.GetRequiredService<ILocalizationReleaseDiffer>();
        if (!endpoints.ServiceProvider.GetServices<ILocalizationExportFormatAdapter>().Any()) throw new InvalidOperationException("Localization management web composition requires at least one export adapter.");
        var options = endpoints.ServiceProvider.GetRequiredService<IOptions<LocalizationManagementWebOptions>>().Value;
        ValidateOptions(options);
        var group = endpoints.MapGroup(options.RoutePrefix).WithTags("Orbyss Forms Localization Management");

        var find = group.MapGet("/catalogs", async (string? search, int? first, int? maximum, ILocalizationCatalogQueries queries, CancellationToken cancellationToken) =>
            Results.Ok(await queries.FindAsync(search, first ?? 0, maximum ?? 100, cancellationToken).ConfigureAwait(false)));
        Protect(find, options.ReadPolicy);

        var getCatalog = group.MapGet("/catalogs/{catalogId}", async (string catalogId, ILocalizationCatalogQueries queries, CancellationToken cancellationToken) =>
        {
            var catalog = await queries.GetCatalogAsync(new LocalizationCatalogId(catalogId), cancellationToken).ConfigureAwait(false);
            return catalog is null ? Results.NotFound() : Results.Ok(catalog);
        });
        Protect(getCatalog, options.ReadPolicy);

        var create = group.MapPost("/catalogs", async (LocalizationCatalogWriteRequest request, ClaimsPrincipal user, ILocalizationCatalogManagement management, CancellationToken cancellationToken) =>
            Results.Ok(await management.CreateAsync(request.Catalog, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(create, options.WritePolicy);

        var replace = group.MapPut("/catalogs/{catalogId}", async (string catalogId, LocalizationCatalogWriteRequest request, ClaimsPrincipal user, ILocalizationCatalogManagement management, CancellationToken cancellationToken) =>
        {
            if (!string.Equals(catalogId, request.Catalog.Id.Value, StringComparison.Ordinal)) return Results.BadRequest();
            return Results.Ok(await management.ReplaceAsync(request.Catalog, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false));
        });
        Protect(replace, options.WritePolicy);

        var validate = group.MapPost("/catalogs/validate", async (LocalizationCatalogDefinition catalog, ILocalizationCatalogManagement management, CancellationToken cancellationToken) =>
            Results.Ok(await management.ValidateAsync(catalog, cancellationToken).ConfigureAwait(false)));
        Protect(validate, options.WritePolicy);

        var preview = group.MapPost("/catalogs/{catalogId}/imports/preview", async (string catalogId, LocalizationImportUploadModel request, ILocalizationCatalogManagement management, CancellationToken cancellationToken) =>
        {
            var content = Decode(request.ContentBase64, options.MaximumImportBytes);
            return Results.Ok(await management.PreviewImportAsync(
                new LocalizationCatalogId(catalogId),
                new LocalizationImportRequest(request.Format, content, request.MergePolicy, request.Scope, request.Mapping, request.SourceName, request.ContentSha256),
                cancellationToken).ConfigureAwait(false));
        }).WithMetadata(new RequestSizeLimitAttribute(checked(((long)options.MaximumImportBytes * 2L) + 65_536L)));
        Protect(preview, options.ImportPolicy);

        var apply = group.MapPost("/catalogs/{catalogId}/imports/{previewId}/apply", async (string catalogId, string previewId, LocalizationImportApplyModel request, ClaimsPrincipal user, ILocalizationCatalogManagement management, CancellationToken cancellationToken) =>
            Results.Ok(await management.ApplyImportAsync(new LocalizationCatalogId(catalogId), previewId, Mutation(request.Mutation, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(apply, options.ImportPolicy);

        var export = group.MapPost("/catalogs/{catalogId}/exports", async (string catalogId, LocalizationExportWebRequest request, ILocalizationCatalogManagement management, IEnumerable<ILocalizationExportFormatAdapter> adapters, CancellationToken cancellationToken) =>
        {
            var catalog = await management.GetAsync(new LocalizationCatalogId(catalogId), cancellationToken).ConfigureAwait(false);
            if (catalog is null) return Results.NotFound();
            var adapter = adapters.SingleOrDefault(item => item.Format == request.Format) ?? throw new InvalidOperationException($"No localization export adapter is registered for '{request.Format}'.");
            var document = await adapter.ExportAsync(new LocalizationExportRequest(request.Format, catalog, request.Scope, request.LanguageTags, request.Mapping, request.SuggestedBaseName), cancellationToken).ConfigureAwait(false);
            return Results.File(document.Content.ToArray(), document.MediaType, document.SuggestedFileName, enableRangeProcessing: false);
        });
        Protect(export, options.ExportPolicy);

        var getRelease = group.MapGet("/releases/{releaseId}", async (string releaseId, ILocalizationCatalogQueries queries, CancellationToken cancellationToken) =>
        {
            var release = await queries.GetReleaseAsync(new LocalizationReleaseId(releaseId), cancellationToken).ConfigureAwait(false);
            return release is null ? Results.NotFound() : Results.Ok(release);
        });
        Protect(getRelease, options.ReadPolicy);

        var diff = group.MapGet("/releases/{baselineId}/diff/{candidateId}", async (string baselineId, string candidateId, ILocalizationCatalogQueries queries, ILocalizationReleaseDiffer differ, CancellationToken cancellationToken) =>
        {
            var baseline = await queries.GetReleaseAsync(new LocalizationReleaseId(baselineId), cancellationToken).ConfigureAwait(false);
            var candidate = await queries.GetReleaseAsync(new LocalizationReleaseId(candidateId), cancellationToken).ConfigureAwait(false);
            return baseline is null || candidate is null ? Results.NotFound() : Results.Ok(await differ.CompareAsync(baseline, candidate, cancellationToken).ConfigureAwait(false));
        });
        Protect(diff, options.ReadPolicy);

        MapLifecycle(group, options);
    }

    /// <summary>Maps review, approval, publication, and retirement mutations.</summary>
    private static void MapLifecycle(RouteGroupBuilder group, LocalizationManagementWebOptions options)
    {
        foreach (var action in new[] { "review", "approve", "publish" })
        {
            var endpoint = group.MapPost($"/catalogs/{{catalogId}}/{{revision:long}}/{action}", async (string catalogId, long revision, LocalizationWebMutation request, ClaimsPrincipal user, ILocalizationReleaseLifecycle lifecycle, CancellationToken cancellationToken) =>
            {
                var mutation = Mutation(request, user, options);
                var id = new LocalizationCatalogId(catalogId);
                var value = new LocalizationRevision(revision);
                return action switch
                {
                    "review" => Results.Ok(await lifecycle.SubmitForReviewAsync(id, value, mutation, cancellationToken).ConfigureAwait(false)),
                    "approve" => Results.Ok(await lifecycle.ApproveAsync(id, value, mutation, cancellationToken).ConfigureAwait(false)),
                    _ => Results.Ok(await lifecycle.PublishAsync(id, value, mutation, cancellationToken).ConfigureAwait(false))
                };
            });
            Protect(endpoint, options.WritePolicy);
        }

        var retire = group.MapPost("/releases/{releaseId}/retire", async (string releaseId, LocalizationWebMutation request, ClaimsPrincipal user, ILocalizationReleaseLifecycle lifecycle, CancellationToken cancellationToken) =>
            Results.Ok(await lifecycle.RetireAsync(new LocalizationReleaseId(releaseId), Mutation(request, user, options), cancellationToken).ConfigureAwait(false)));
        Protect(retire, options.WritePolicy);
    }

    /// <summary>Builds an audit mutation from client command data and authenticated server claims.</summary>
    private static LocalizationMutationContext Mutation(LocalizationWebMutation request, ClaimsPrincipal user, LocalizationManagementWebOptions options)
    {
        if (string.IsNullOrWhiteSpace(request.IdempotencyKey) || request.RequestedAt == default) throw new BadHttpRequestException("A mutation requires an idempotency key and audit timestamp.");
        var subject = user.FindFirst(options.SubjectClaimType)?.Value ?? user.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrWhiteSpace(subject)) throw new BadHttpRequestException("The authenticated principal has no configured subject claim.");
        var kind = user.FindFirst(options.ActorKindClaimType)?.Value ?? "user";
        var displayName = user.FindFirst(options.DisplayNameClaimType)?.Value ?? user.Identity?.Name;
        return new LocalizationMutationContext(request.IdempotencyKey, string.IsNullOrWhiteSpace(request.ExpectedVersion) ? null : new LocalizationConcurrencyToken(request.ExpectedVersion), new LocalizationAuditActor(subject, kind, displayName), request.RequestedAt, request.CorrelationId);
    }

    /// <summary>Decodes one bounded base64 upload without permitting oversized allocation.</summary>
    private static byte[] Decode(string content, int maximumBytes)
    {
        var maximumEncodedLength = (((long)maximumBytes + 2L) / 3L) * 4L;
        if (string.IsNullOrWhiteSpace(content) || content.Length > maximumEncodedLength) throw new BadHttpRequestException("Localization import content is empty or exceeds the configured limit.");
        try
        {
            var bytes = Convert.FromBase64String(content);
            if (bytes.Length > maximumBytes) throw new BadHttpRequestException("Localization import content exceeds the configured limit.");
            return bytes;
        }
        catch (FormatException)
        {
            throw new BadHttpRequestException("Localization import content is not valid base64.");
        }
    }

    /// <summary>Applies a named authorization policy or the consumer's default authenticated policy.</summary>
    private static void Protect(RouteHandlerBuilder endpoint, string? policy)
    {
        if (string.IsNullOrWhiteSpace(policy)) endpoint.RequireAuthorization();
        else endpoint.RequireAuthorization(policy);
    }

    /// <summary>Rejects invalid route, upload, or claim configuration at shell startup.</summary>
    private static void ValidateOptions(LocalizationManagementWebOptions options)
    {
        if (options.RoutePrefix.Length is < 2 or > 128 || !options.RoutePrefix.StartsWith("/", StringComparison.Ordinal) || options.RoutePrefix.EndsWith("/", StringComparison.Ordinal) || options.RoutePrefix.Contains("//", StringComparison.Ordinal) || options.RoutePrefix.Contains('{') || options.RoutePrefix.Contains('?') || options.RoutePrefix.Contains('#')) throw new InvalidOperationException("Localization management route prefix must be a fixed absolute path without a trailing slash.");
        if (options.MaximumImportBytes is < 1 or > 67_108_864 || string.IsNullOrWhiteSpace(options.SubjectClaimType) || string.IsNullOrWhiteSpace(options.ActorKindClaimType) || string.IsNullOrWhiteSpace(options.DisplayNameClaimType)) throw new InvalidOperationException("Localization management bounds and claim mappings are invalid.");
    }
}
