using CShells;
using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;

namespace ProgramKit.Web.Discovery;

/// <summary>Composes an optional public document projection into one shell, leaving the Host neutral.</summary>
[ShellFeature(
    name: "ProgramKit.Web.Discovery",
    DisplayName = "Program Kit Web Discovery",
    Description = "Serves an explicit public HTML, sitemap, robots and optional Markdown projection.")]
public sealed class ProgramKitDiscoveryFeature(ShellSettings settings) : IWebShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.Configure<DiscoveryOptions>(settings.GetConfigurationRoot().GetSection(DiscoveryOptions.SectionName));
        services.TryAddSingleton<IPublicDocumentCatalog>(provider => new FilePublicDocumentCatalog(
            provider.GetRequiredService<IHostEnvironment>().ContentRootPath,
            provider.GetRequiredService<IOptions<DiscoveryOptions>>().Value.OutputDirectory));
    }

    /// <inheritdoc />
    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment)
    {
        var documents = endpoints.ServiceProvider.GetRequiredService<IPublicDocumentCatalog>().ReadDocuments();
        var routes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var document in documents)
        {
            FilePublicDocumentCatalog.ValidateRoute(document.Route);
            FilePublicDocumentCatalog.ValidateContentType(document.ContentType);
            if (!routes.Add(document.Route))
            {
                throw new InvalidDataException("Discovery catalogue has duplicate routes.");
            }
        }

        foreach (var document in documents)
        {
            var bytes = document.Content.ToArray();
            endpoints.MapMethods(document.Route, ["GET", "HEAD"], (HttpContext context) =>
            {
                context.Response.Headers.XContentTypeOptions = "nosniff";
                if (!document.Index)
                {
                    context.Response.Headers["X-Robots-Tag"] = "noindex";
                }

                return Results.Bytes(bytes, document.ContentType);
            }).AllowAnonymous().ExcludeFromDescription();
        }
    }
}
