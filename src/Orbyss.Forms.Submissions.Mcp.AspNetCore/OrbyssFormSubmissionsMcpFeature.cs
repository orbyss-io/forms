using CShells;
using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using ModelContextProtocol.Server;
using Orbyss.Forms.Submissions.Tool;
using Orbyss.Foundation.Mcp.AspNetCore;

namespace Orbyss.Forms.Submissions.Mcp.AspNetCore;

/// <summary>Contributes authenticated owner-scoped form tools to the shared MCP transport.</summary>
[ShellFeature(name: "Orbyss.Forms.Submissions.Mcp.AspNetCore", DisplayName = "Orbyss Forms Submissions MCP", Description = "Contributes governed owner-scoped draft, submission, and attachment tools to the shared MCP transport.", DependsOn = [typeof(FoundationMcpFeature)])]
public sealed class OrbyssFormSubmissionsMcpFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.Configure<FormSubmissionsMcpOptions>(settings.GetConfigurationRoot().GetSection(FormSubmissionsMcpOptions.SectionName));
        services.TryAddSingleton<IFormToolActorProvider>(provider =>
        {
            var options = provider.GetRequiredService<IOptions<FormSubmissionsMcpOptions>>().Value;
            ValidateOptions(options);
            return new ClaimsFormSubmissionToolActorProvider(new FormSubmissionToolIdentityOptions(options.SubjectClaimType, options.ActorKindClaimType, options.DisplayNameClaimType));
        });
        services.AddMcpServer().WithTools<FormOperationsTools>();
    }

    /// <summary>Rejects incomplete claim mappings when the contributor is activated.</summary>
    private static void ValidateOptions(FormSubmissionsMcpOptions options)
    {
        if (string.IsNullOrWhiteSpace(options.SubjectClaimType) || string.IsNullOrWhiteSpace(options.ActorKindClaimType) || string.IsNullOrWhiteSpace(options.DisplayNameClaimType)) throw new InvalidOperationException("Form MCP claim mappings are required.");
    }
}
