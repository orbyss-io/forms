using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Orbyss.Forms;

/// <summary>Composes the complete process-local Forms storage adapter for tests and development.</summary>
[ShellFeature(
    name: "Orbyss.Forms.Storage.InMemory",
    DisplayName = "Orbyss Forms In-Memory Storage",
    Description = "Provides bounded process-local definition, release, submission, attachment, and attachment-content persistence.")]
public sealed class OrbyssFormsInMemoryStorageFeature : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.TryAddSingleton(new InMemoryFormStorageOptions());
        services.TryAddSingleton<InMemoryFormDefinitionStore>();
        services.TryAddSingleton<InMemoryFormReleaseStore>();
        services.TryAddSingleton<InMemoryFormSubmissionStore>();
        services.TryAddSingleton<InMemoryFormAttachmentStore>();
        services.TryAddSingleton<InMemoryFormAttachmentContentStore>();
        services.TryAddSingleton<IFormDefinitionStore>(provider => provider.GetRequiredService<InMemoryFormDefinitionStore>());
        services.TryAddSingleton<IFormReleaseStore>(provider => provider.GetRequiredService<InMemoryFormReleaseStore>());
        services.TryAddSingleton<IFormReleaseRetirementStore>(provider => provider.GetRequiredService<InMemoryFormReleaseStore>());
        services.TryAddSingleton<IFormSubmissionStore>(provider => provider.GetRequiredService<InMemoryFormSubmissionStore>());
        services.TryAddSingleton<IFormAttachmentStore>(provider => provider.GetRequiredService<InMemoryFormAttachmentStore>());
        services.TryAddSingleton<IFormAttachmentContentStore>(provider => provider.GetRequiredService<InMemoryFormAttachmentContentStore>());
    }
}
