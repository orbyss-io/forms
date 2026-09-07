using CShells;
using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using ModelContextProtocol.Server;
using Orbyss.Forms.Tool;
using Orbyss.Foundation.Mcp.AspNetCore;

namespace Orbyss.Forms.Mcp.AspNetCore;

/// <summary>Contributes authenticated owner-scoped form tools to the shared MCP transport.</summary>
[ShellFeature(name: "Orbyss.Forms.Mcp.AspNetCore", DisplayName = "Orbyss Forms Form Operations MCP", Description = "Contributes governed owner-scoped form operation tools to the shared MCP transport.", DependsOn = [typeof(FoundationMcpFeature)])]
public sealed class OrbyssFormMcpFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.Configure<FormMcpWebOptions>(settings.GetConfigurationRoot().GetSection(FormMcpWebOptions.SectionName));
        services.TryAddSingleton<IFormToolActorProvider>(provider =>
        {
            var options = provider.GetRequiredService<IOptions<FormMcpWebOptions>>().Value;
            ValidateOptions(options);
            return new ClaimsFormToolActorProvider(new FormToolIdentityOptions(options.SubjectClaimType, options.ActorKindClaimType, options.DisplayNameClaimType));
        });
        services.AddMcpServer().WithTools<FormOperationsTools>();
    }

    /// <summary>Rejects incomplete claim mappings when the contributor is activated.</summary>
    private static void ValidateOptions(FormMcpWebOptions options)
    {
        if (string.IsNullOrWhiteSpace(options.SubjectClaimType) || string.IsNullOrWhiteSpace(options.ActorKindClaimType) || string.IsNullOrWhiteSpace(options.DisplayNameClaimType)) throw new InvalidOperationException("Form MCP claim mappings are required.");
    }
}
