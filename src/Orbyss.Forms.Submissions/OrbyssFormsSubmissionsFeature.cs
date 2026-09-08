using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace Orbyss.Forms;

/// <summary>Registers the default draft, submission, validation, and attachment services.</summary>
[ShellFeature(
    name: "Orbyss.Forms.Submissions",
    DisplayName = "Orbyss Forms Submissions",
    Description = "Provides resumable drafts, authoritative submissions, and fail-closed attachment handling.")]
public sealed class OrbyssFormsSubmissionsFeature : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.TryAddSingleton(new FormSubmissionOptions());
        services.TryAddSingleton<IFormDataValidator, DefaultFormDataValidator>();
        services.TryAddSingleton<IFormAttachmentPolicy, RejectingFormAttachmentPolicy>();
        services.TryAddSingleton<IFormAttachmentScanner, RejectingFormAttachmentScanner>();
        services.TryAddSingleton<DefaultFormSubmissionService>();
        services.TryAddSingleton<IFormDraftOperations>(provider => provider.GetRequiredService<DefaultFormSubmissionService>());
        services.TryAddSingleton<IFormDraftMigrationOperations>(provider => provider.GetRequiredService<DefaultFormSubmissionService>());
        services.TryAddSingleton<IFormSubmissionOperations>(provider => provider.GetRequiredService<DefaultFormSubmissionService>());
        services.TryAddSingleton<IFormSubmissionReview>(provider => provider.GetRequiredService<DefaultFormSubmissionService>());
        services.TryAddSingleton<DefaultFormAttachmentService>();
        services.TryAddSingleton<IFormAttachmentOperations>(provider => provider.GetRequiredService<DefaultFormAttachmentService>());
    }
}
