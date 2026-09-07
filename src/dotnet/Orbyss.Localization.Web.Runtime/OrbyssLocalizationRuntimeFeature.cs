using CShells;
using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace Orbyss.Localization.Web.Runtime;

/// <summary>Composes immutable localization resolution and bundle reads into one selected shell.</summary>
[ShellFeature(
    name: "Orbyss.Localization.Web.Runtime",
    DisplayName = "Orbyss Forms Localization Runtime",
    Description = "Provides independently configurable immutable message and bundle endpoints.")]
public sealed class OrbyssLocalizationRuntimeFeature(ShellSettings settings) : IWebShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) =>
        services.Configure<LocalizationRuntimeWebOptions>(settings.GetConfigurationRoot().GetSection(LocalizationRuntimeWebOptions.SectionName));

    /// <inheritdoc />
    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment)
    {
        _ = endpoints.ServiceProvider.GetRequiredService<ILocalizationRuntime>();
        var options = endpoints.ServiceProvider.GetRequiredService<IOptions<LocalizationRuntimeWebOptions>>().Value;
        ValidateOptions(options);
        var group = endpoints.MapGroup(options.RoutePrefix).WithTags("Orbyss Forms Localization Runtime");

        var bundle = group.MapGet("/bundles/{scopeKind}/{languageTag}", async (HttpContext context, string scopeKind, string languageTag, string? resourceId, string? parentResourceId, ILocalizationRuntime runtime, CancellationToken cancellationToken) =>
        {
            if (!Enum.TryParse<LocalizationScopeKind>(scopeKind, true, out var kind)) return Results.BadRequest();
            var result = await runtime.GetBundleAsync(new LocalizationScope(kind, resourceId, parentResourceId), languageTag, cancellationToken).ConfigureAwait(false);
            if (result is null) return Results.NotFound();
            Headers(context, result.Sha256, options);
            if (Matches(context, result.Sha256)) return Results.StatusCode(StatusCodes.Status304NotModified);
            return Results.Ok(result);
        });
        Access(bundle, options);

        var message = group.MapGet("/messages/{scopeKind}/{languageTag}/{key}", async (HttpContext context, string scopeKind, string languageTag, string key, string? resourceId, string? parentResourceId, ILocalizationRuntime runtime, CancellationToken cancellationToken) =>
        {
            if (!Enum.TryParse<LocalizationScopeKind>(scopeKind, true, out var kind)) return Results.BadRequest();
            var result = await runtime.ResolveAsync(new LocalizationScope(kind, resourceId, parentResourceId), key, languageTag, cancellationToken).ConfigureAwait(false);
            if (result is null) return Results.NotFound();
            var etag = Hash(result);
            Headers(context, etag, options);
            if (Matches(context, etag)) return Results.StatusCode(StatusCodes.Status304NotModified);
            return Results.Ok(result);
        });
        Access(message, options);
    }

    /// <summary>Applies explicit anonymous access or the consumer-selected authorization policy.</summary>
    private static void Access(RouteHandlerBuilder endpoint, LocalizationRuntimeWebOptions options)
    {
        if (options.AllowAnonymous) endpoint.AllowAnonymous();
        else if (string.IsNullOrWhiteSpace(options.AuthorizationPolicy)) endpoint.RequireAuthorization();
        else endpoint.RequireAuthorization(options.AuthorizationPolicy);
    }

    /// <summary>Writes cache, entity-tag, and content-sniffing response headers.</summary>
    private static void Headers(HttpContext context, string etag, LocalizationRuntimeWebOptions options)
    {
        context.Response.Headers.ETag = $"\"{etag}\"";
        context.Response.Headers.CacheControl = $"{(options.AllowAnonymous ? "public" : "private")},max-age={options.CacheSeconds}";
        context.Response.Headers.XContentTypeOptions = "nosniff";
    }

    /// <summary>Checks a request entity tag using exact opaque comparison.</summary>
    private static bool Matches(HttpContext context, string etag) =>
        context.Request.Headers.IfNoneMatch.Any(value => string.Equals(value, $"\"{etag}\"", StringComparison.Ordinal));

    /// <summary>Creates a deterministic entity tag for one immutable resolution.</summary>
    private static string Hash(LocalizationResolution resolution)
    {
        var value = $"{resolution.Scope.Kind}\n{resolution.Scope.ParentResourceId}\n{resolution.Scope.ResourceId}\n{resolution.Key}\n{resolution.RequestedLanguageTag}\n{resolution.ResolvedLanguageTag}\n{resolution.Direction}\n{resolution.Pattern}\n{resolution.UsedFallback}";
        return Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(value)));
    }

    /// <summary>Rejects invalid route and cache configuration at shell startup.</summary>
    private static void ValidateOptions(LocalizationRuntimeWebOptions options)
    {
        if (options.RoutePrefix.Length is < 2 or > 128 || !options.RoutePrefix.StartsWith("/", StringComparison.Ordinal) || options.RoutePrefix.EndsWith("/", StringComparison.Ordinal) || options.RoutePrefix.Contains("//", StringComparison.Ordinal) || options.RoutePrefix.Contains('{') || options.RoutePrefix.Contains('?') || options.RoutePrefix.Contains('#')) throw new InvalidOperationException("Localization runtime route prefix must be a fixed absolute path without a trailing slash.");
        if (options.CacheSeconds is < 0 or > 86_400) throw new InvalidOperationException("Localization runtime cache duration must be between zero and one day.");
    }
}
