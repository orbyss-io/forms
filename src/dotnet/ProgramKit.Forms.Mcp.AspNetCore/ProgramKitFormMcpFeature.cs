using CShells;
using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using ModelContextProtocol.Server;
using ProgramKit.Forms.Tool;
using ProgramKit.Mcp.AspNetCore;

namespace ProgramKit.Forms.Mcp.AspNetCore;

/// <summary>Contributes authenticated owner-scoped form tools to the shared MCP transport.</summary>
[ShellFeature(name: "ProgramKit.Forms.Mcp.AspNetCore", DisplayName = "Program Kit Form Operations MCP", Description = "Contributes governed owner-scoped form operation tools to the shared MCP transport.", DependsOn = [typeof(ProgramKitMcpFeature)])]
public sealed class ProgramKitFormMcpFeature(ShellSettings settings) : IShellFeature
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
