using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Orbyss.Forms;

/// <summary>Registers the default form catalog, lifecycle, query, and compatibility services.</summary>
[ShellFeature(
    name: "Orbyss.Forms.Management",
    DisplayName = "Orbyss Forms Management",
    Description = "Provides form authoring, catalog queries, compatibility analysis, and governed release lifecycle behavior.",
    DependsOn = [typeof(OrbyssFormsJsonFormsFeature)])]
public sealed class OrbyssFormsManagementFeature : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.TryAddSingleton<IFormCompatibilityAnalyzer, DefaultFormCompatibilityAnalyzer>();
        services.TryAddSingleton<DefaultFormCatalogService>();
        services.TryAddSingleton<IFormAuthoring>(provider => provider.GetRequiredService<DefaultFormCatalogService>());
        services.TryAddSingleton<IFormCatalogQueries>(provider => provider.GetRequiredService<DefaultFormCatalogService>());
        services.TryAddSingleton<IFormReleaseLifecycle>(provider => provider.GetRequiredService<DefaultFormCatalogService>());
    }
}
