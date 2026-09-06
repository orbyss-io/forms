namespace ProgramKit.Localization;

/// <summary>Persists editable catalogs through atomic concurrency, idempotency, and audit semantics.</summary>
public interface ILocalizationCatalogStore
{
    /// <summary>Gets the current catalog snapshot, or returns null when it does not exist.</summary>
    ValueTask<LocalizationCatalogSnapshot?> GetAsync(
        LocalizationCatalogId catalogId,
        CancellationToken cancellationToken = default);

    /// <summary>Enumerates current catalog snapshots without imposing a provider cursor contract.</summary>
    IAsyncEnumerable<LocalizationCatalogSnapshot> FindAsync(
        CancellationToken cancellationToken = default);

    /// <summary>Returns an exact durable command replay, or null when the key has not been observed.</summary>
    ValueTask<LocalizationCatalogPersistenceResult?> ReplayAsync(
        LocalizationCatalogId catalogId,
        string idempotencyKey,
        string fingerprint,
        CancellationToken cancellationToken = default);

    /// <summary>Atomically writes or replays an exact catalog command.</summary>
    ValueTask<LocalizationCatalogPersistenceResult> WriteAsync(
        LocalizationCatalogPersistenceCommand command,
        CancellationToken cancellationToken = default);
}
