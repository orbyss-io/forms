using CShells;
using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using ModelContextProtocol.Server;
using ProgramKit.Localization.Tool;
using ProgramKit.Mcp.AspNetCore;

namespace ProgramKit.Localization.Mcp.AspNetCore;

/// <summary>Contributes governed localization tools to the shared MCP transport.</summary>
[ShellFeature(name: "ProgramKit.Localization.Mcp.AspNetCore", DisplayName = "Program Kit Localization MCP", Description = "Contributes governed localization management and runtime tools to the shared MCP transport.", DependsOn = [typeof(ProgramKitMcpFeature)])]
public sealed class ProgramKitLocalizationMcpFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.Configure<LocalizationMcpOptions>(settings.GetConfigurationRoot().GetSection(LocalizationMcpOptions.SectionName));
        services.TryAddSingleton<ILocalizationToolActorProvider>(provider =>
        {
            var options = RequiredOptions(provider);
            return new ClaimsLocalizationToolActorProvider(new LocalizationToolIdentityOptions(options.SubjectClaimType, options.ActorKindClaimType, options.DisplayNameClaimType));
        });
        services.TryAddSingleton(provider =>
        {
            var options = RequiredOptions(provider);
            return new LocalizationToolTransferOptions(options.MaximumImportBytes, options.MaximumExportBytes);
        });
        services.AddMcpServer().WithTools<LocalizationManagementTools>();
    }

    /// <summary>Resolves and validates contributor options.</summary>
    private static LocalizationMcpOptions RequiredOptions(IServiceProvider provider)
    {
        var options = provider.GetRequiredService<IOptions<LocalizationMcpOptions>>().Value;
        if (string.IsNullOrWhiteSpace(options.SubjectClaimType) || string.IsNullOrWhiteSpace(options.ActorKindClaimType) || string.IsNullOrWhiteSpace(options.DisplayNameClaimType)) throw new InvalidOperationException("Localization MCP claim mappings are required.");
        if (options.MaximumImportBytes is < 1 or > 67_108_864 || options.MaximumExportBytes is < 1 or > 67_108_864) throw new InvalidOperationException("Localization MCP transfer limits must be from one byte through 64 MiB.");
        return options;
    }
}
