using System.Runtime.CompilerServices;
using System.Text.Json;

namespace Orbyss.Forms;

/// <summary>Stores immutable form releases and separate retirement state in process memory.</summary>
public sealed class InMemoryFormReleaseStore : IFormReleaseStore, IFormReleaseRetirementStore
{
    /// <summary>Serializes immutable release and retirement access.</summary>
    private readonly object gate = new();
    /// <summary>Holds exact canonical immutable release payloads.</summary>
    private readonly Dictionary<string, string> releases = new(StringComparer.Ordinal);
    /// <summary>Holds separate retirement replay state.</summary>
    private readonly Dictionary<string, InMemoryFormRetirement> retirements = new(StringComparer.Ordinal);
    /// <summary>Bounds release count.</summary>
    private readonly InMemoryFormStorageOptions options;

    /// <summary>Initializes an empty bounded release store.</summary>
    public InMemoryFormReleaseStore(InMemoryFormStorageOptions? options = null)
    {
        this.options = options ?? new InMemoryFormStorageOptions();
        InMemoryFormStorageCodec.Validate(this.options);
    }

    /// <inheritdoc />
    public ValueTask WriteAsync(FormRelease release, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        ArgumentNullException.ThrowIfNull(release); ArgumentException.ThrowIfNullOrWhiteSpace(release.Id.Value);
        if (release.Retired) throw new InvalidOperationException("Immutable form release content must be written before separate retirement state.");
        var payload = JsonSerializer.Serialize(release, InMemoryFormStorageCodec.Options);
        InMemoryFormStorageCodec.EnsureSize(release, options.MaximumDocumentBytes);
        lock (gate)
        {
            if (releases.TryGetValue(release.Id.Value, out var existing))
            {
                if (!string.Equals(existing, payload, StringComparison.Ordinal)) throw new InvalidOperationException("An immutable form release identifier already contains different content.");
                return ValueTask.CompletedTask;
            }
            if (releases.Count >= options.MaximumDocuments) throw new InvalidOperationException("The in-memory form release limit was reached.");
            releases.Add(release.Id.Value, payload);
            return ValueTask.CompletedTask;
        }
    }

    /// <inheritdoc />
    public ValueTask<FormRelease?> GetAsync(FormReleaseId releaseId, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(releaseId);
        lock (gate) return ValueTask.FromResult(releases.TryGetValue(releaseId.Value, out var payload) ? Read(payload) with { Retired = retirements.ContainsKey(releaseId.Value) } : null);
    }

    /// <inheritdoc />
    public async IAsyncEnumerable<FormRelease> FindByFormAsync(FormId formId, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(formId); ArgumentException.ThrowIfNullOrWhiteSpace(formId.Value);
        FormRelease[] found;
        lock (gate) found = releases.Values.Select(Read).Where(item => item.Candidate.FormId == formId).Select(item => item with { Retired = retirements.ContainsKey(item.Id.Value) }).OrderBy(item => item.PublishedAt).ThenBy(item => item.Id.Value, StringComparer.Ordinal).ToArray();
        foreach (var release in found) { cancellationToken.ThrowIfCancellationRequested(); yield return release; await Task.Yield(); }
    }

    /// <inheritdoc />
    public ValueTask<FormMutationResult<FormRelease>> RetireAsync(FormReleaseId releaseId, string fingerprint, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateId(releaseId); ValidateMutation(fingerprint, mutation);
        lock (gate)
        {
            if (!releases.TryGetValue(releaseId.Value, out var payload)) throw new KeyNotFoundException("The form release does not exist.");
            var release = Read(payload);
            if (retirements.TryGetValue(releaseId.Value, out var previous))
            {
                if (!string.Equals(previous.IdempotencyKey, mutation.IdempotencyKey, StringComparison.Ordinal) || !string.Equals(previous.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The form release is already retired by another command.");
                return ValueTask.FromResult(new FormMutationResult<FormRelease>(release with { Retired = true }, previous.Version, true));
            }
            if (mutation.ExpectedVersion is null || !string.Equals(mutation.ExpectedVersion.Value, release.Candidate.CandidateSha256, StringComparison.Ordinal)) throw new InvalidOperationException("The form release concurrency token does not match.");
            var retired = release with { Retired = true };
            var version = new FormConcurrencyToken(InMemoryFormStorageCodec.Hash(retired));
            retirements.Add(releaseId.Value, new InMemoryFormRetirement(mutation.IdempotencyKey, fingerprint, version));
            return ValueTask.FromResult(new FormMutationResult<FormRelease>(retired, version, false));
        }
    }

    /// <summary>Deserializes a detached immutable release.</summary>
    private static FormRelease Read(string payload) => JsonSerializer.Deserialize<FormRelease>(payload, InMemoryFormStorageCodec.Options) ?? throw new InvalidDataException("The in-memory form release has no payload.");
    /// <summary>Rejects missing release identifiers.</summary>
    private static void ValidateId(FormReleaseId id) { ArgumentNullException.ThrowIfNull(id); ArgumentException.ThrowIfNullOrWhiteSpace(id.Value); }
    /// <summary>Rejects incomplete retirement evidence.</summary>
    private static void ValidateMutation(string fingerprint, FormMutationContext mutation)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(fingerprint); ArgumentNullException.ThrowIfNull(mutation); ArgumentException.ThrowIfNullOrWhiteSpace(mutation.IdempotencyKey); ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Id); ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Kind);
        if (mutation.RequestedAt == default) throw new ArgumentException("A form mutation timestamp is required.", nameof(mutation));
    }
}
