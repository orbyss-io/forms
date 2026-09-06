namespace ProgramKit.Localization;

/// <summary>Provides bounded localization management queries without exposing provider cursors.</summary>
public interface ILocalizationCatalogQueries
{
    /// <summary>Gets one editable catalog and its current opaque version, or returns null when absent.</summary>
    ValueTask<LocalizationCatalogDocument?> GetCatalogAsync(
        LocalizationCatalogId catalogId,
        CancellationToken cancellationToken = default);

    /// <summary>Finds localization catalogs by a bounded free-text search.</summary>
    ValueTask<LocalizationPage<LocalizationCatalogItem>> FindAsync(
        string? search = null,
        int first = 0,
        int maximum = 100,
        CancellationToken cancellationToken = default);

    /// <summary>Gets one immutable localization release, or returns null when absent.</summary>
    ValueTask<LocalizationRelease?> GetReleaseAsync(
        LocalizationReleaseId releaseId,
        CancellationToken cancellationToken = default);
}
