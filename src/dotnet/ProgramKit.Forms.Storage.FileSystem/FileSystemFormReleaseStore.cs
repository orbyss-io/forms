using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ProgramKit.Forms;

/// <summary>Stores immutable form releases as atomic, digest-verified filesystem documents.</summary>
public sealed class FileSystemFormReleaseStore : IFormReleaseStore, IFormReleaseRetirementStore
{
    /// <summary>Holds stable serialization settings used for both persistence and replay comparison.</summary>
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = false
    };

    /// <summary>Serializes retirement writes for one release in the current process.</summary>
    private static readonly ConcurrentDictionary<string, SemaphoreSlim> RetirementGates = new(StringComparer.OrdinalIgnoreCase);

    /// <summary>Holds the resolved owned directory for form release documents.</summary>
    private readonly string directoryPath;

    /// <summary>Initializes a store rooted in an explicit consumer-owned directory.</summary>
    public FileSystemFormReleaseStore(FileSystemFormReleaseStoreOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentException.ThrowIfNullOrWhiteSpace(options.DirectoryPath);
        directoryPath = Path.GetFullPath(options.DirectoryPath);
        Directory.CreateDirectory(directoryPath);
    }

    /// <inheritdoc />
    public async ValueTask WriteAsync(FormRelease release, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(release);
        ArgumentException.ThrowIfNullOrWhiteSpace(release.Id.Value);
        if (release.Retired) throw new InvalidOperationException("Immutable form release content must be written before separate retirement state.");
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
    public async ValueTask<FormRelease?> GetAsync(
        FormReleaseId releaseId,
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
        var release = JsonSerializer.Deserialize<FormRelease>(payload, SerializerOptions)
            ?? throw new InvalidDataException($"Form release document '{path}' has no payload.");
        if (!string.Equals(release.Id.Value, releaseId.Value, StringComparison.Ordinal))
        {
            throw new InvalidDataException($"Form release document '{path}' does not match its requested identifier.");
        }

        return await ApplyRetirementAsync(release, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<FormRelease> FindByFormAsync(
        FormId formId,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(formId);
        ArgumentException.ThrowIfNullOrWhiteSpace(formId.Value);
        var releases = new List<FormRelease>();
        foreach (var path in Directory.EnumerateFiles(directoryPath, "*.form-release.json", SearchOption.TopDirectoryOnly))
        {
            cancellationToken.ThrowIfCancellationRequested();
            var payload = await ReadPayloadAsync(path, cancellationToken).ConfigureAwait(false);
            var release = JsonSerializer.Deserialize<FormRelease>(payload, SerializerOptions)
                ?? throw new InvalidDataException($"Form release document '{path}' has no payload.");
            if (release.Candidate.FormId == formId)
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
    public async ValueTask<FormMutationResult<FormRelease>> RetireAsync(
        FormReleaseId releaseId,
        string fingerprint,
        FormMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(releaseId);
        ArgumentNullException.ThrowIfNull(mutation);
        ArgumentException.ThrowIfNullOrWhiteSpace(releaseId.Value);
        ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.IdempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Kind);
        if (mutation.RequestedAt == default) throw new ArgumentException("A form mutation timestamp is required.", nameof(mutation));
        var retirementPath = RetirementPath(releaseId);
        var gate = RetirementGates.GetOrAdd(retirementPath, _ => new SemaphoreSlim(1, 1));
        await gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var releasePath = ReleasePath(releaseId);
            if (!File.Exists(releasePath)) throw new KeyNotFoundException("The form release does not exist.");
            var payload = await ReadPayloadAsync(releasePath, cancellationToken).ConfigureAwait(false);
            var release = DeserializeRelease(payload, releasePath);
            if (File.Exists(retirementPath))
            {
                var previous = await ReadRetirementAsync(retirementPath, cancellationToken).ConfigureAwait(false);
                RequireRetirementMatches(previous, release, retirementPath);
                if (!string.Equals(previous.IdempotencyKey, mutation.IdempotencyKey, StringComparison.Ordinal) || !string.Equals(previous.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form release is already retired by another command.");
                return new FormMutationResult<FormRelease>(release with { Retired = true }, previous.Version, true);
            }

            if (mutation.ExpectedVersion is null || !string.Equals(mutation.ExpectedVersion.Value, release.Candidate.CandidateSha256, StringComparison.Ordinal)) throw new InvalidOperationException("The form release concurrency token does not match.");
            var version = RetiredVersion(release);
            var retirement = new StoredFormRetirement(mutation.IdempotencyKey, fingerprint, mutation.Actor, mutation.RequestedAt, mutation.CorrelationId, version);
            await WriteCreateOnlyAsync(retirementPath, Document(JsonSerializer.Serialize(retirement, SerializerOptions)), cancellationToken).ConfigureAwait(false);
            return new FormMutationResult<FormRelease>(release with { Retired = true }, version, false);
        }
        finally { gate.Release(); }
    }

    /// <summary>Maps an untrusted release identifier to a fixed-length filename.</summary>
    private string ReleasePath(FormReleaseId releaseId) =>
        Path.Combine(directoryPath, Hash(releaseId.Value) + ".form-release.json");

    /// <summary>Maps a release identifier to its separate retirement sidecar.</summary>
    private string RetirementPath(FormReleaseId releaseId) =>
        Path.Combine(directoryPath, Hash(releaseId.Value) + ".form-retirement.json");

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
            throw new InvalidOperationException("An immutable form release identifier already contains different content.");
        }
    }

    /// <summary>Reads and verifies an envelope before exposing its serialized release payload.</summary>
    private static async ValueTask<string> ReadPayloadAsync(string path, CancellationToken cancellationToken)
    {
        var content = await File.ReadAllTextAsync(path, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
        var document = JsonNode.Parse(content)?.AsObject()
            ?? throw new InvalidDataException($"Form release document '{path}' is invalid JSON.");
        var payload = document["payload"]?.GetValue<string>()
            ?? throw new InvalidDataException($"Form release document '{path}' has no payload.");
        var digest = document["sha256"]?.GetValue<string>()
            ?? throw new InvalidDataException($"Form release document '{path}' has no digest.");
        if (!string.Equals(digest, Hash(payload), StringComparison.Ordinal))
        {
            throw new InvalidDataException($"Form release document '{path}' failed content verification.");
        }

        return payload;
    }

    /// <summary>Applies separate retirement state without changing release content.</summary>
    private async ValueTask<FormRelease> ApplyRetirementAsync(FormRelease release, CancellationToken cancellationToken)
    {
        var path = RetirementPath(release.Id);
        if (!File.Exists(path)) return release;
        var retirement = await ReadRetirementAsync(path, cancellationToken).ConfigureAwait(false);
        RequireRetirementMatches(retirement, release, path);
        return release with { Retired = true };
    }

    /// <summary>Reads and verifies one retirement sidecar.</summary>
    private static async ValueTask<StoredFormRetirement> ReadRetirementAsync(string path, CancellationToken cancellationToken)
    {
        var payload = await ReadPayloadAsync(path, cancellationToken).ConfigureAwait(false);
        var retirement = JsonSerializer.Deserialize<StoredFormRetirement>(payload, SerializerOptions) ?? throw new InvalidDataException($"Form retirement document '{path}' has no payload.");
        if (string.IsNullOrWhiteSpace(retirement.IdempotencyKey) || string.IsNullOrWhiteSpace(retirement.Fingerprint) || string.IsNullOrWhiteSpace(retirement.Actor.Id) || string.IsNullOrWhiteSpace(retirement.Actor.Kind) || retirement.RetiredAt == default || string.IsNullOrWhiteSpace(retirement.Version.Value)) throw new InvalidDataException($"Form retirement document '{path}' has invalid audit or replay metadata.");
        return retirement;
    }

    /// <summary>Requires retirement state to be bound to immutable release content.</summary>
    private static void RequireRetirementMatches(StoredFormRetirement retirement, FormRelease release, string path)
    {
        if (retirement.Version != RetiredVersion(release)) throw new InvalidDataException($"Form retirement document '{path}' does not match its immutable release.");
    }

    /// <summary>Creates the opaque version for a retired immutable release.</summary>
    private static FormConcurrencyToken RetiredVersion(FormRelease release) => new(Hash(JsonSerializer.Serialize(release with { Retired = true }, SerializerOptions)));
    /// <summary>Deserializes one verified immutable release payload.</summary>
    private static FormRelease DeserializeRelease(string payload, string path) => JsonSerializer.Deserialize<FormRelease>(payload, SerializerOptions) ?? throw new InvalidDataException($"Form release document '{path}' has no payload.");

    /// <summary>Creates one sidecar atomically without overwriting prior state.</summary>
    private static async ValueTask WriteCreateOnlyAsync(string path, string content, CancellationToken cancellationToken)
    {
        var temporary = Path.Combine(Path.GetDirectoryName(path)!, $".{Path.GetFileName(path)}.{Guid.NewGuid():N}.tmp");
        try
        {
            await File.WriteAllTextAsync(temporary, content, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
            File.Move(temporary, path, overwrite: false);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    /// <summary>Computes a lowercase SHA-256 digest for filenames and content verification.</summary>
    private static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
