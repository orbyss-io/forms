using CShells;
using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using ModelContextProtocol.AspNetCore;
using ModelContextProtocol.Server;

namespace ProgramKit.Mcp.AspNetCore;

/// <summary>Composes one authenticated stateless MCP transport for selected tool contributors.</summary>
[ShellFeature(name: "ProgramKit.Mcp.AspNetCore", DisplayName = "Program Kit MCP Transport", Description = "Provides the shared authenticated stateless Streamable HTTP endpoint for explicit Program Kit tool contributors.")]
public sealed class ProgramKitMcpFeature(ShellSettings settings) : IWebShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.Configure<ProgramKitMcpWebOptions>(settings.GetConfigurationRoot().GetSection(ProgramKitMcpWebOptions.SectionName));
        services.AddMcpServer().WithHttpTransport(options => options.Stateless = true);
    }

    /// <inheritdoc />
    public void MapEndpoints(IEndpointRouteBuilder endpoints, IHostEnvironment? environment)
    {
        var options = endpoints.ServiceProvider.GetRequiredService<IOptions<ProgramKitMcpWebOptions>>().Value;
        ValidateOptions(options);
        var mapped = endpoints.MapMcp(options.Route);
        if (string.IsNullOrWhiteSpace(options.Policy)) mapped.RequireAuthorization();
        else mapped.RequireAuthorization(options.Policy);
    }

    /// <summary>Rejects unsafe routes at shell startup.</summary>
    private static void ValidateOptions(ProgramKitMcpWebOptions options)
    {
        if (options.Route.Length is < 2 or > 128 || !options.Route.StartsWith("/", StringComparison.Ordinal) || options.Route.EndsWith("/", StringComparison.Ordinal) || options.Route.Contains("//", StringComparison.Ordinal) || options.Route.IndexOfAny(['{', '?', '#']) >= 0) throw new InvalidOperationException("The Program Kit MCP route must be a fixed absolute path without a trailing slash.");
    }
}
