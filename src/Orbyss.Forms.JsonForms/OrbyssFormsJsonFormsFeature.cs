using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Orbyss.Forms;

/// <summary>Registers the default form-definition validator and JSON Forms compiler.</summary>
[ShellFeature(
    name: "Orbyss.Forms.JsonForms",
    DisplayName = "Orbyss Forms JSON Forms",
    Description = "Provides bounded semantic definition validation and deterministic JSON Forms artifact compilation.")]
public sealed class OrbyssFormsJsonFormsFeature : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.TryAddSingleton(new FormValidationOptions());
        services.TryAddSingleton<IFormDefinitionValidator>(provider =>
            new FormDefinitionValidator(provider.GetRequiredService<FormValidationOptions>()));
        services.TryAddSingleton<IFormCompiler, JsonFormsCompiler>();
    }
}
