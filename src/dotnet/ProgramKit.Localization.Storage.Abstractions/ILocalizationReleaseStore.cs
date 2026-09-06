namespace ProgramKit.Localization;

/// <summary>Persists and retrieves immutable published localization releases.</summary>
public interface ILocalizationReleaseStore
{
    /// <summary>Writes a release once, accepting only byte-equivalent idempotent replays.</summary>
    ValueTask WriteAsync(LocalizationRelease release, CancellationToken cancellationToken = default);

    /// <summary>Gets an immutable release, or returns null when it is absent.</summary>
    ValueTask<LocalizationRelease?> GetAsync(
        LocalizationReleaseId releaseId,
        CancellationToken cancellationToken = default);

    /// <summary>Lists immutable releases for one catalog in publication order.</summary>
    IAsyncEnumerable<LocalizationRelease> FindByCatalogAsync(
        LocalizationCatalogId catalogId,
        CancellationToken cancellationToken = default);
}
