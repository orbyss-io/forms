using CShells;
using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Orbyss.Forms;

/// <summary>Composes the complete single-process filesystem Forms storage adapter.</summary>
[ShellFeature(
    name: "Orbyss.Forms.Storage.FileSystem",
    DisplayName = "Orbyss Forms File-System Storage",
    Description = "Provides content-verified definition, release, submission, attachment, and attachment-content persistence.")]
public sealed class OrbyssFormsFileSystemStorageFeature(ShellSettings settings) : IShellFeature
{
    /// <summary>Configuration section for the owned storage root.</summary>
    public const string SectionName = "Orbyss:Forms:Storage:FileSystem";

    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        var configuredRoot = settings.GetConfigurationRoot().GetSection(SectionName)["RootPath"];
        var root = Path.GetFullPath(string.IsNullOrWhiteSpace(configuredRoot)
            ? Path.Combine(AppContext.BaseDirectory, "App_Data", "forms")
            : configuredRoot);
        services.TryAddSingleton(new FileSystemFormDefinitionStoreOptions(Path.Combine(root, "definitions")));
        services.TryAddSingleton(new FileSystemFormReleaseStoreOptions(Path.Combine(root, "releases")));
        services.TryAddSingleton(new FileSystemFormOperationalStoreOptions(Path.Combine(root, "operations")));
        services.TryAddSingleton<FileSystemFormDefinitionStore>();
        services.TryAddSingleton<FileSystemFormReleaseStore>();
        services.TryAddSingleton<FileSystemFormSubmissionStore>();
        services.TryAddSingleton<FileSystemFormAttachmentStore>();
        services.TryAddSingleton<FileSystemFormAttachmentContentStore>();
        services.TryAddSingleton<IFormDefinitionStore>(provider => provider.GetRequiredService<FileSystemFormDefinitionStore>());
        services.TryAddSingleton<IFormReleaseStore>(provider => provider.GetRequiredService<FileSystemFormReleaseStore>());
        services.TryAddSingleton<IFormReleaseRetirementStore>(provider => provider.GetRequiredService<FileSystemFormReleaseStore>());
        services.TryAddSingleton<IFormSubmissionStore>(provider => provider.GetRequiredService<FileSystemFormSubmissionStore>());
        services.TryAddSingleton<IFormAttachmentStore>(provider => provider.GetRequiredService<FileSystemFormAttachmentStore>());
        services.TryAddSingleton<IFormAttachmentContentStore>(provider => provider.GetRequiredService<FileSystemFormAttachmentContentStore>());
    }
}
