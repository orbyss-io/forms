using CShells;
using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace Orbyss.Forms.Web.Runtime;

/// <summary>Composes immutable current and identified form-release reads into one selected shell.</summary>
[ShellFeature(name: "Orbyss.Forms.Web.Runtime", DisplayName = "Orbyss Forms Form Runtime", Description = "Provides independently configurable immutable form release endpoints.")]
public sealed class OrbyssFormRuntimeFeature(ShellSettings settings) : IWebShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) => services.Configure<FormRuntimeWebOptions>(settings.GetConfigurationRoot().GetSection(FormRuntimeWebOptions.SectionName));

    /// <inheritdoc />
    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment)
    {
        _ = endpoints.ServiceProvider.GetRequiredService<IFormCatalogQueries>();
        var options = endpoints.ServiceProvider.GetRequiredService<IOptions<FormRuntimeWebOptions>>().Value;
        ValidateOptions(options);
        var group = endpoints.MapGroup(options.RoutePrefix).WithTags("Orbyss Forms Form Runtime");
        var byId = group.MapGet("/releases/{releaseId}", async (HttpContext context, string releaseId, IFormCatalogQueries queries, CancellationToken cancellationToken) =>
        {
            var release = await queries.GetReleaseAsync(new FormReleaseId(releaseId), cancellationToken).ConfigureAwait(false);
            return Response(context, release, options);
        });
        Access(byId, options);
        var current = group.MapGet("/forms/{formId}/current", async (HttpContext context, string formId, IFormCatalogQueries queries, CancellationToken cancellationToken) =>
        {
            var release = await queries.GetCurrentReleaseAsync(new FormId(formId), cancellationToken).ConfigureAwait(false);
            return Response(context, release, options);
        });
        Access(current, options);
    }

    /// <summary>Creates one cache-aware response for a nonretired immutable release.</summary>
    private static IResult Response(HttpContext context, FormRelease? release, FormRuntimeWebOptions options)
    {
        if (release is null || release.Retired) return Results.NotFound();
        var etag = release.Candidate.CandidateSha256;
        context.Response.Headers.ETag = $"\"{etag}\"";
        context.Response.Headers.CacheControl = $"{(options.AllowAnonymous ? "public" : "private")},max-age={options.CacheSeconds}";
        context.Response.Headers.XContentTypeOptions = "nosniff";
        if (context.Request.Headers.IfNoneMatch.Any(value => string.Equals(value, $"\"{etag}\"", StringComparison.Ordinal))) return Results.StatusCode(StatusCodes.Status304NotModified);
        return Results.Ok(release);
    }

    /// <summary>Applies explicit anonymous access or the host-selected authorization policy.</summary>
    private static void Access(RouteHandlerBuilder endpoint, FormRuntimeWebOptions options)
    {
        if (options.AllowAnonymous) endpoint.AllowAnonymous();
        else if (string.IsNullOrWhiteSpace(options.AuthorizationPolicy)) endpoint.RequireAuthorization();
        else endpoint.RequireAuthorization(options.AuthorizationPolicy);
    }

    /// <summary>Rejects invalid route and cache configuration at startup.</summary>
    private static void ValidateOptions(FormRuntimeWebOptions options)
    {
        if (options.RoutePrefix.Length is < 2 or > 128 || !options.RoutePrefix.StartsWith("/", StringComparison.Ordinal) || options.RoutePrefix.EndsWith("/", StringComparison.Ordinal) || options.RoutePrefix.Contains("//", StringComparison.Ordinal) || options.RoutePrefix.IndexOfAny(['{', '?', '#']) >= 0) throw new InvalidOperationException("Form runtime route prefix must be a fixed absolute path without a trailing slash.");
        if (options.CacheSeconds is < 0 or > 86_400) throw new InvalidOperationException("Form runtime cache duration must be between zero and one day.");
    }
}
