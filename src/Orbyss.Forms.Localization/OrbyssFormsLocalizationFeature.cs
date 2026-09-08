using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Orbyss.Forms.Localization;

/// <summary>Registers the explicit bridge between Forms translation requirements and Localization contracts.</summary>
[ShellFeature(
    name: "Orbyss.Forms.Localization",
    DisplayName = "Orbyss Forms Localization Bridge",
    Description = "Provides the opt-in bridge without selecting or solidifying a Localization implementation.")]
public sealed class OrbyssFormsLocalizationFeature : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services) =>
        services.TryAddSingleton<IFormLocalizationBridge, DefaultFormLocalizationBridge>();
}
