namespace Orbyss.Forms;

/// <summary>Transforms draft data between exact immutable form releases through trusted application code.</summary>
public interface IFormDraftDataMigration
{
    /// <summary>Gets the stable allowlisted migration identity.</summary>
    string Id { get; }

    /// <summary>Transforms one source document without mutating releases or persisted state.</summary>
    ValueTask<string> MigrateAsync(
        FormRelease source,
        FormRelease target,
        FormDataDocument data,
        CancellationToken cancellationToken = default);
}
