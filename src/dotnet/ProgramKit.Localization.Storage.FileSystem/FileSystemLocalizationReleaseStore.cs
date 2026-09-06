using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ProgramKit.Localization;

/// <summary>Stores immutable localization releases as atomic, digest-verified filesystem documents.</summary>
public sealed class FileSystemLocalizationReleaseStore : ILocalizationReleaseStore, ILocalizationReleaseRetirementStore
{
    /// <summary>Holds stable serialization settings used for persistence and replay comparison.</summary>
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = false
    };

    /// <summary>Serializes retirement writes to one release within the current process.</summary>
    private static readonly ConcurrentDictionary<string, SemaphoreSlim> RetirementGates = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Holds the resolved owned directory for localization release documents.</summary>
    private readonly string directoryPath;

    /// <summary>Initializes a store rooted in an explicit consumer-owned directory.</summary>
    public FileSystemLocalizationReleaseStore(FileSystemLocalizationReleaseStoreOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentException.ThrowIfNullOrWhiteSpace(options.DirectoryPath);
        directoryPath = Path.GetFullPath(options.DirectoryPath);
        Directory.CreateDirectory(directoryPath);
    }

    /// <inheritdoc />
    public async ValueTask WriteAsync(LocalizationRelease release, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(release);
        ArgumentException.ThrowIfNullOrWhiteSpace(release.Id.Value);
        if (release.Retired) throw new InvalidOperationException("Immutable localization release content must be written before separate retirement state.");
        cancellationToken.ThrowIfCancellationRequested();
        var payload = JsonSerializer.Serialize(release, SerializerOptions);
        var document = Document(payload);
        var target = ReleasePath(release.Id);
        if (File.Exists(target))
        {
            await RequireReplayAsync(target, payload, cancellationToken).ConfigureAwait(false);
            return;
        }

        var temporary = Path.Combine(directoryPath, $".{Path.GetFileName(target)}.{Guid.NewGuid():N}.tmp");
        try
        {
            await File.WriteAllTextAsync(temporary, document, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
            try
            {
                File.Move(temporary, target, overwrite: false);
            }
            catch (IOException) when (File.Exists(target))
            {
                await RequireReplayAsync(target, payload, cancellationToken).ConfigureAwait(false);
            }
        }
        finally
        {
            if (File.Exists(temporary))
            {
                File.Delete(temporary);
            }
        }
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationRelease?> GetAsync(
        LocalizationReleaseId releaseId,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(releaseId);
        ArgumentException.ThrowIfNullOrWhiteSpace(releaseId.Value);
        var path = ReleasePath(releaseId);
        if (!File.Exists(path))
        {
            return null;
        }

        var payload = await ReadPayloadAsync(path, cancellationToken).ConfigureAwait(false);
        var release = DeserializeRelease(payload, path);
        if (!string.Equals(release.Id.Value, releaseId.Value, StringComparison.Ordinal))
        {
            throw new InvalidDataException($"Localization release document '{path}' does not match its requested identifier.");
        }

        return await ApplyRetirementAsync(release, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<LocalizationRelease> FindByCatalogAsync(
        LocalizationCatalogId catalogId,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(catalogId);
        ArgumentException.ThrowIfNullOrWhiteSpace(catalogId.Value);
        var releases = new List<LocalizationRelease>();
        foreach (var path in Directory.EnumerateFiles(directoryPath, "*.localization-release.json", SearchOption.TopDirectoryOnly))
        {
            cancellationToken.ThrowIfCancellationRequested();
            var payload = await ReadPayloadAsync(path, cancellationToken).ConfigureAwait(false);
            var release = DeserializeRelease(payload, path);
            if (release.CatalogId == catalogId)
            {
                releases.Add(await ApplyRetirementAsync(release, cancellationToken).ConfigureAwait(false));
            }
        }

        foreach (var release in releases.OrderBy(item => item.PublishedAt).ThenBy(item => item.Id.Value, StringComparer.Ordinal))
        {
            yield return release;
        }
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationMutationResult<LocalizationRelease>> RetireAsync(
        LocalizationReleaseId releaseId,
        string fingerprint,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(releaseId);
        ArgumentNullException.ThrowIfNull(mutation);
        ArgumentException.ThrowIfNullOrWhiteSpace(releaseId.Value);
        ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.IdempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Kind);
        if (mutation.RequestedAt == default) throw new ArgumentException("A localization mutation timestamp is required.", nameof(mutation));
        var retirementPath = RetirementPath(releaseId);
        var gate = RetirementGates.GetOrAdd(retirementPath, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var releasePath = ReleasePath(releaseId);
            if (!File.Exists(releasePath)) throw new KeyNotFoundException("The localization release does not exist.");
            var payload = await ReadPayloadAsync(releasePath, cancellationToken).ConfigureAwait(false);
            var release = DeserializeRelease(payload, releasePath);
            if (File.Exists(retirementPath))
            {
                var previous = await ReadRetirementAsync(retirementPath, cancellationToken).ConfigureAwait(false);
                RequireRetirementMatches(previous, release, retirementPath);
                if (!string.Equals(previous.IdempotencyKey, mutation.IdempotencyKey, StringComparison.Ordinal)
                    || !string.Equals(previous.Fingerprint, fingerprint, StringComparison.Ordinal))
                {
                    throw new InvalidOperationException("The localization release is already retired by another command.");
                }

                return new LocalizationMutationResult<LocalizationRelease>(release with { Retired = true }, previous.Version, true);
            }

            if (mutation.ExpectedVersion is null || !string.Equals(mutation.ExpectedVersion.Value, release.Sha256, StringComparison.Ordinal))
            {
                throw new InvalidOperationException("The localization release concurrency token does not match.");
            }

            var retired = release with { Retired = true };
            var version = RetiredVersion(release);
            var retirement = new StoredLocalizationRetirement(mutation.IdempotencyKey, fingerprint, mutation.Actor, mutation.RequestedAt, mutation.CorrelationId, version);
            await WriteCreateOnlyAsync(retirementPath, Document(JsonSerializer.Serialize(retirement, SerializerOptions)), cancellationToken).ConfigureAwait(false);
            return new LocalizationMutationResult<LocalizationRelease>(retired, version, false);
        }
        finally
        {
            gate.Release();
        }
    }

    /// <summary>Maps an untrusted release identifier to a fixed-length filename.</summary>
    private string ReleasePath(LocalizationReleaseId releaseId) =>
        Path.Combine(directoryPath, Hash(releaseId.Value) + ".localization-release.json");

    /// <summary>Maps an untrusted release identifier to its separate retirement-state filename.</summary>
    private string RetirementPath(LocalizationReleaseId releaseId) =>
        Path.Combine(directoryPath, Hash(releaseId.Value) + ".localization-retirement.json");

    /// <summary>Creates a content-digest envelope without changing the serialized release payload.</summary>
    private static string Document(string payload) => new JsonObject
    {
        ["sha256"] = Hash(payload),
        ["payload"] = payload
    }.ToJsonString(SerializerOptions);

    /// <summary>Requires an existing release to contain the exact canonical replay payload.</summary>
    private static async ValueTask RequireReplayAsync(
        string path,
        string expectedPayload,
        CancellationToken cancellationToken)
    {
        var existingPayload = await ReadPayloadAsync(path, cancellationToken).ConfigureAwait(false);
        if (!string.Equals(existingPayload, expectedPayload, StringComparison.Ordinal))
        {
            throw new InvalidOperationException("An immutable localization release identifier already contains different content.");
        }
    }

    /// <summary>Reads and verifies an envelope before exposing its serialized release payload.</summary>
    private static async ValueTask<string> ReadPayloadAsync(string path, CancellationToken cancellationToken)
    {
        var content = await File.ReadAllTextAsync(path, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
        var document = JsonNode.Parse(content)?.AsObject()
            ?? throw new InvalidDataException($"Localization release document '{path}' is invalid JSON.");
        var payload = document["payload"]?.GetValue<string>()
            ?? throw new InvalidDataException($"Localization release document '{path}' has no payload.");
        var digest = document["sha256"]?.GetValue<string>()
            ?? throw new InvalidDataException($"Localization release document '{path}' has no digest.");
        if (!string.Equals(digest, Hash(payload), StringComparison.Ordinal))
        {
            throw new InvalidDataException($"Localization release document '{path}' failed content verification.");
        }

        return payload;
    }

    /// <summary>Applies separately stored retirement state without changing immutable release content.</summary>
    private async ValueTask<LocalizationRelease> ApplyRetirementAsync(
        LocalizationRelease release,
        CancellationToken cancellationToken)
    {
        var path = RetirementPath(release.Id);
        if (!File.Exists(path)) return release;
        var retirement = await ReadRetirementAsync(path, cancellationToken).ConfigureAwait(false);
        RequireRetirementMatches(retirement, release, path);
        return release with { Retired = true };
    }

    /// <summary>Reads and verifies one retirement sidecar.</summary>
    private static async ValueTask<StoredLocalizationRetirement> ReadRetirementAsync(
        string path,
        CancellationToken cancellationToken)
    {
        var payload = await ReadPayloadAsync(path, cancellationToken).ConfigureAwait(false);
        var retirement = JsonSerializer.Deserialize<StoredLocalizationRetirement>(payload, SerializerOptions)
            ?? throw new InvalidDataException($"Localization retirement document '{path}' has no payload.");
        if (string.IsNullOrWhiteSpace(retirement.IdempotencyKey)
            || string.IsNullOrWhiteSpace(retirement.Fingerprint)
            || string.IsNullOrWhiteSpace(retirement.Actor.Id)
            || string.IsNullOrWhiteSpace(retirement.Actor.Kind)
            || retirement.RetiredAt == default
            || string.IsNullOrWhiteSpace(retirement.Version.Value))
        {
            throw new InvalidDataException($"Localization retirement document '{path}' has invalid audit or replay metadata.");
        }

        return retirement;
    }

    /// <summary>Requires a retirement sidecar to be bound to the immutable release content.</summary>
    private static void RequireRetirementMatches(
        StoredLocalizationRetirement retirement,
        LocalizationRelease release,
        string path)
    {
        if (retirement.Version != RetiredVersion(release)) throw new InvalidDataException($"Localization retirement document '{path}' does not match its immutable release.");
    }

    /// <summary>Creates the opaque state version for one retired immutable release.</summary>
    private static LocalizationConcurrencyToken RetiredVersion(LocalizationRelease release) =>
        new(Hash(JsonSerializer.Serialize(release with { Retired = true }, SerializerOptions)));

    /// <summary>Deserializes one verified immutable release payload.</summary>
    private static LocalizationRelease DeserializeRelease(string payload, string path) =>
        JsonSerializer.Deserialize<LocalizationRelease>(payload, SerializerOptions)
            ?? throw new InvalidDataException($"Localization release document '{path}' has no payload.");

    /// <summary>Creates one sidecar atomically and never overwrites existing state.</summary>
    private static async ValueTask WriteCreateOnlyAsync(
        string path,
        string content,
        CancellationToken cancellationToken)
    {
        var temporary = Path.Combine(Path.GetDirectoryName(path)!, $".{Path.GetFileName(path)}.{Guid.NewGuid():N}.tmp");
        try
        {
            await File.WriteAllTextAsync(temporary, content, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
            File.Move(temporary, path, overwrite: false);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }

    /// <summary>Computes a lowercase SHA-256 digest for filenames and content verification.</summary>
    private static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
