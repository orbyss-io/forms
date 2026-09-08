namespace Orbyss.Forms;

/// <summary>Provides bounded management and runtime form queries without exposing provider cursors.</summary>
public interface IFormCatalogQueries
{
    /// <summary>Gets one editable definition and its current opaque version, or returns null when absent.</summary>
    ValueTask<FormDefinitionDocument?> GetDefinitionAsync(
        FormId formId,
        CancellationToken cancellationToken = default);

    /// <summary>Finds forms by a bounded free-text search.</summary>
    ValueTask<FormPage<FormCatalogItem>> FindAsync(
        string? search = null,
        int first = 0,
        int maximum = 100,
        CancellationToken cancellationToken = default);

    /// <summary>Gets one immutable release, or returns null when it does not exist.</summary>
    ValueTask<FormRelease?> GetReleaseAsync(
        FormReleaseId releaseId,
        CancellationToken cancellationToken = default);

    /// <summary>Gets the current nonretired release for a form, or returns null when unavailable.</summary>
    ValueTask<FormRelease?> GetCurrentReleaseAsync(
        FormId formId,
        CancellationToken cancellationToken = default);
}
