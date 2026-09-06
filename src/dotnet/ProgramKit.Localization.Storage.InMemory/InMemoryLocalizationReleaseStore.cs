using System.Runtime.CompilerServices;
using System.Text.Json;

namespace ProgramKit.Localization;

/// <summary>Stores immutable localization releases and separate retirement state in process memory.</summary>
public sealed class InMemoryLocalizationReleaseStore : ILocalizationReleaseStore, ILocalizationReleaseRetirementStore
{
    /// <summary>Serializes immutable release and retirement access.</summary>
    private readonly object gate = new();
    /// <summary>Holds exact canonical immutable release payloads.</summary>
    private readonly Dictionary<string, string> releases = new(StringComparer.Ordinal);
    /// <summary>Holds separate retirement replay state.</summary>
    private readonly Dictionary<string, InMemoryLocalizationRetirement> retirements = new(StringComparer.Ordinal);
    /// <summary>Bounds release count.</summary>
    private readonly InMemoryLocalizationStorageOptions options;

    /// <summary>Initializes an empty bounded release store.</summary>
    public InMemoryLocalizationReleaseStore(InMemoryLocalizationStorageOptions? options = null)
    {
        this.options = options ?? new InMemoryLocalizationStorageOptions(); InMemoryLocalizationStorageCodec.Validate(this.options);
    }

    /// <inheritdoc />
    public ValueTask WriteAsync(LocalizationRelease release, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ArgumentNullException.ThrowIfNull(release); ArgumentException.ThrowIfNullOrWhiteSpace(release.Id.Value);
        if (release.Retired) throw new InvalidOperationException("Immutable localization release content must be written before separate retirement state.");
        var payload = JsonSerializer.Serialize(release, InMemoryLocalizationStorageCodec.Options);
        InMemoryLocalizationStorageCodec.EnsureSize(release, options.MaximumDocumentBytes);
        lock (gate)
        {
            if (releases.TryGetValue(release.Id.Value, out var existing))
            {
                if (!string.Equals(existing, payload, StringComparison.Ordinal)) throw new InvalidOperationException("An immutable localization release identifier already contains different content.");
                return ValueTask.CompletedTask;
            }
            if (releases.Count >= options.MaximumDocuments) throw new InvalidOperationException("The in-memory localization release limit was reached.");
            releases.Add(release.Id.Value, payload); return ValueTask.CompletedTask;
        }
    }

    /// <inheritdoc />
    public ValueTask<LocalizationRelease?> GetAsync(LocalizationReleaseId releaseId, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(releaseId);
        lock (gate) return ValueTask.FromResult(releases.TryGetValue(releaseId.Value, out var payload) ? Read(payload) with { Retired = retirements.ContainsKey(releaseId.Value) } : null);
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<LocalizationRelease> FindByCatalogAsync(LocalizationCatalogId catalogId, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(catalogId); ArgumentException.ThrowIfNullOrWhiteSpace(catalogId.Value); LocalizationRelease[] found;
        lock (gate) found = releases.Values.Select(Read).Where(item => item.CatalogId == catalogId).Select(item => item with { Retired = retirements.ContainsKey(item.Id.Value) }).OrderBy(item => item.PublishedAt).ThenBy(item => item.Id.Value, StringComparer.Ordinal).ToArray();
        foreach (var release in found) { cancellationToken.ThrowIfCancellationRequested(); yield return release; await Task.Yield(); }
    }

    /// <inheritdoc />
    public ValueTask<LocalizationMutationResult<LocalizationRelease>> RetireAsync(LocalizationReleaseId releaseId, string fingerprint, LocalizationMutationContext mutation, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(releaseId); ValidateMutation(fingerprint, mutation);
        lock (gate)
        {
            if (!releases.TryGetValue(releaseId.Value, out var payload)) throw new KeyNotFoundException("The localization release does not exist.");
            var release = Read(payload);
            if (retirements.TryGetValue(releaseId.Value, out var previous))
            {
                if (!string.Equals(previous.IdempotencyKey, mutation.IdempotencyKey, StringComparison.Ordinal) || !string.Equals(previous.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The localization release is already retired by another command.");
                return ValueTask.FromResult(new LocalizationMutationResult<LocalizationRelease>(release with { Retired = true }, previous.Version, true));
            }
            if (mutation.ExpectedVersion is null || !string.Equals(mutation.ExpectedVersion.Value, release.Sha256, StringComparison.Ordinal)) throw new InvalidOperationException("The localization release concurrency token does not match.");
            var retired = release with { Retired = true };
            var version = new LocalizationConcurrencyToken(InMemoryLocalizationStorageCodec.Hash(retired));
            retirements.Add(releaseId.Value, new InMemoryLocalizationRetirement(mutation.IdempotencyKey, fingerprint, version));
            return ValueTask.FromResult(new LocalizationMutationResult<LocalizationRelease>(retired, version, false));
        }
    }

    /// <summary>Deserializes a detached immutable release.</summary>
    private static LocalizationRelease Read(string payload) => JsonSerializer.Deserialize<LocalizationRelease>(payload, InMemoryLocalizationStorageCodec.Options) ?? throw new InvalidDataException("The in-memory localization release has no payload.");
    /// <summary>Rejects missing release identifiers.</summary>
    private static void ValidateId(LocalizationReleaseId id) { ArgumentNullException.ThrowIfNull(id); ArgumentException.ThrowIfNullOrWhiteSpace(id.Value); }
    /// <summary>Rejects incomplete retirement evidence.</summary>
    private static void ValidateMutation(string fingerprint, LocalizationMutationContext mutation)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint); ArgumentNullException.ThrowIfNull(mutation); ArgumentException.ThrowIfNullOrWhiteSpace(mutation.IdempotencyKey); ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Id); ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Kind);
        if (mutation.RequestedAt == default) throw new ArgumentException("A localization mutation timestamp is required.", nameof(mutation));
    }
}
