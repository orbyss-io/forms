namespace ProgramKit.Forms;

/// <summary>Migrates active owner-scoped drafts to newer immutable releases.</summary>
public interface IFormDraftMigrationOperations
{
    /// <summary>Migrates a draft, requiring a trusted handler when compatibility is breaking.</summary>
    ValueTask<FormMutationResult<FormDraft>> MigrateAsync(
        FormDraftId draftId,
        FormReleaseId targetReleaseId,
        string? migrationId,
        FormMutationContext mutation,
        CancellationToken cancellationToken = default);
}
