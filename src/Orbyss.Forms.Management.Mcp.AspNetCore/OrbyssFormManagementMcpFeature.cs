using CShells;
using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using ModelContextProtocol.Server;
using Orbyss.Forms.Management.Tool;
using Orbyss.Forms.Tool;
using Orbyss.Foundation.Mcp.AspNetCore;

namespace Orbyss.Forms.Management.Mcp.AspNetCore;

/// <summary>Contributes governed form-management tools to the shared MCP transport.</summary>
[ShellFeature(name: "Orbyss.Forms.Management.Mcp.AspNetCore", DisplayName = "Orbyss Forms Form Management MCP", Description = "Contributes governed form authoring and release tools to the shared MCP transport.", DependsOn = [typeof(FoundationMcpFeature)])]
public sealed class OrbyssFormManagementMcpFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.Configure<FormManagementMcpOptions>(settings.GetConfigurationRoot().GetSection(FormManagementMcpOptions.SectionName));
        services.TryAddSingleton<IFormToolActorProvider>(provider =>
        {
            var options = provider.GetRequiredService<IOptions<FormManagementMcpOptions>>().Value;
            ValidateOptions(options);
            return new ClaimsFormToolActorProvider(new FormToolIdentityOptions(options.SubjectClaimType, options.ActorKindClaimType, options.DisplayNameClaimType));
        });
        services.AddMcpServer().WithTools<FormManagementTools>();
    }

    /// <summary>Rejects incomplete claim mappings when the contributor is activated.</summary>
    private static void ValidateOptions(FormManagementMcpOptions options)
    {
        if (string.IsNullOrWhiteSpace(options.SubjectClaimType) || string.IsNullOrWhiteSpace(options.ActorKindClaimType) || string.IsNullOrWhiteSpace(options.DisplayNameClaimType)) throw new InvalidOperationException("Form management MCP claim mappings are required.");
    }
}
