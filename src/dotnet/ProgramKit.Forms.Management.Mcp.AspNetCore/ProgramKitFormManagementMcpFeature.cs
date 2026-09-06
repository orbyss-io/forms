using CShells;
using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using ModelContextProtocol.Server;
using ProgramKit.Forms.Management.Tool;
using ProgramKit.Forms.Tool;
using ProgramKit.Mcp.AspNetCore;

namespace ProgramKit.Forms.Management.Mcp.AspNetCore;

/// <summary>Contributes governed form-management tools to the shared MCP transport.</summary>
[ShellFeature(name: "ProgramKit.Forms.Management.Mcp.AspNetCore", DisplayName = "Program Kit Form Management MCP", Description = "Contributes governed form authoring and release tools to the shared MCP transport.", DependsOn = [typeof(ProgramKitMcpFeature)])]
public sealed class ProgramKitFormManagementMcpFeature(ShellSettings settings) : IShellFeature
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
