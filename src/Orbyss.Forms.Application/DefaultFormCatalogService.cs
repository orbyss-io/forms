using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Orbyss.Forms;

/// <summary>Orchestrates governed form authoring, compilation, lifecycle, publication, and queries.</summary>
public sealed class DefaultFormCatalogService : IFormAuthoring, IFormCatalogQueries, IFormReleaseLifecycle
{
    /// <summary>Uses stable web serialization for durable command fingerprints.</summary>
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web) { WriteIndented = false };
    /// <summary>Persists editable definitions and their prepared review evidence.</summary>
    private readonly IFormDefinitionStore definitions;
    /// <summary>Persists immutable published releases.</summary>
    private readonly IFormReleaseStore releases;
    /// <summary>Persists mutable retirement state separately from releases.</summary>
    private readonly IFormReleaseRetirementStore retirements;
    /// <summary>Validates provider-neutral definitions.</summary>
    private readonly IFormDefinitionValidator validator;
    /// <summary>Compiles provider-neutral definitions into deterministic artifacts.</summary>
    private readonly IFormCompiler compiler;

    /// <summary>Initializes orchestration over explicitly selected form services and stores.</summary>
    public DefaultFormCatalogService(IFormDefinitionStore definitions, IFormReleaseStore releases, IFormReleaseRetirementStore retirements, IFormDefinitionValidator validator, IFormCompiler compiler)
    {
        this.definitions = definitions ?? throw new ArgumentNullException(nameof(definitions));
        this.releases = releases ?? throw new ArgumentNullException(nameof(releases));
        this.retirements = retirements ?? throw new ArgumentNullException(nameof(retirements));
        this.validator = validator ?? throw new ArgumentNullException(nameof(validator));
        this.compiler = compiler ?? throw new ArgumentNullException(nameof(compiler));
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormDefinition>> CreateAsync(FormDefinition definition, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(definition);
        ValidateMutation(mutation, expectedVersionRequired: false);
        var fingerprint = Fingerprint("create", definition, mutation);
        var replay = await definitions.ReplayAsync(definition.Id, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return DefinitionResult(replay);
        if (definition.Revision.Value != 1 || definition.State != FormLifecycleState.Draft) throw new InvalidOperationException("A form must begin as draft revision 1.");
        await RequireValidAsync(definition, cancellationToken).ConfigureAwait(false);
        return await PersistAsync("create", fingerprint, definition, null, [], mutation, requireAbsent: true, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public async ValueTask<FormDefinition?> GetAsync(FormId formId, CancellationToken cancellationToken = default) => (await definitions.GetAsync(formId, cancellationToken).ConfigureAwait(false))?.Definition;

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormDefinition>> ReplaceAsync(FormDefinition definition, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(definition);
        ValidateMutation(mutation, expectedVersionRequired: true);
        var fingerprint = Fingerprint("replace", definition, mutation);
        var replay = await definitions.ReplayAsync(definition.Id, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return DefinitionResult(replay);
        var current = await RequiredDefinitionAsync(definition.Id, cancellationToken).ConfigureAwait(false);
        RequireExpectedVersion(mutation, current.Version);
        if (current.Definition.State is not (FormLifecycleState.Draft or FormLifecycleState.Published)) throw new InvalidOperationException("A form under review or awaiting publication cannot be replaced.");
        if (definition.Revision.Value != current.Definition.Revision.Value + 1 || definition.State != FormLifecycleState.Draft) throw new InvalidOperationException("A replacement must create the next draft form revision.");
        await RequireValidAsync(definition, cancellationToken).ConfigureAwait(false);
        return await PersistAsync("replace", fingerprint, definition, null, [], mutation, requireAbsent: false, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public ValueTask<IReadOnlyList<FormDiagnostic>> ValidateAsync(FormDefinition definition, CancellationToken cancellationToken = default) => validator.ValidateAsync(definition, cancellationToken);

    /// <inheritdoc />
    public async ValueTask<FormDefinitionDocument?> GetDefinitionAsync(FormId formId, CancellationToken cancellationToken = default)
    {
        var snapshot = await definitions.GetAsync(formId, cancellationToken).ConfigureAwait(false);
        return snapshot is null ? null : new FormDefinitionDocument(snapshot.Definition, snapshot.Version);
    }

    /// <inheritdoc />
    public async ValueTask<FormPage<FormCatalogItem>> FindAsync(string? search = null, int first = 0, int maximum = 100, CancellationToken cancellationToken = default)
    {
        if (first < 0) throw new ArgumentOutOfRangeException(nameof(first), "The form page offset cannot be negative.");
        if (maximum is < 1 or > 1000) throw new ArgumentOutOfRangeException(nameof(maximum), "The form page size must be from 1 through 1000.");
        var normalized = search?.Trim();
        var matches = new List<FormCatalogItem>();
        await foreach (var snapshot in definitions.FindAsync(cancellationToken).ConfigureAwait(false))
        {
            if (!string.IsNullOrEmpty(normalized) && !snapshot.Definition.Id.Value.Contains(normalized, StringComparison.OrdinalIgnoreCase) && !snapshot.Definition.Name.Contains(normalized, StringComparison.OrdinalIgnoreCase)) continue;
            matches.Add(new FormCatalogItem(snapshot.Definition.Id, snapshot.Definition.Name, snapshot.Definition.Revision, snapshot.Definition.State, snapshot.Version));
        }
        var ordered = matches.OrderBy(item => item.Name, StringComparer.OrdinalIgnoreCase).ThenBy(item => item.Id.Value, StringComparer.Ordinal).ToArray();
        return new FormPage<FormCatalogItem>(ordered.Skip(first).Take(maximum).ToArray(), ordered.Length);
    }

    /// <inheritdoc />
    public ValueTask<FormRelease?> GetReleaseAsync(FormReleaseId releaseId, CancellationToken cancellationToken = default) => releases.GetAsync(releaseId, cancellationToken);

    /// <inheritdoc />
    public async ValueTask<FormRelease?> GetCurrentReleaseAsync(FormId formId, CancellationToken cancellationToken = default)
    {
        FormRelease? current = null;
        await foreach (var release in releases.FindByFormAsync(formId, cancellationToken).ConfigureAwait(false)) if (!release.Retired) current = release;
        return current;
    }

    /// <inheritdoc />
    public async ValueTask<FormCandidate> CompileAsync(FormId formId, FormRevision revision, CancellationToken cancellationToken = default)
    {
        var current = await RequiredDefinitionAsync(formId, cancellationToken).ConfigureAwait(false);
        RequireRevision(current.Definition, revision);
        if (current.Candidate is not null) return current.Candidate;
        var compiledAt = current.AuditTrail.Count == 0 ? DateTimeOffset.UnixEpoch : current.AuditTrail[^1].RequestedAt;
        return await compiler.CompileAsync(current.Definition, compiledAt, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormLifecycleState>> SubmitForReviewAsync(FormId formId, FormRevision revision, IReadOnlyList<string> evidence, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(evidence);
        ValidateMutation(mutation, expectedVersionRequired: true);
        var normalizedEvidence = NormalizeEvidence(evidence);
        var fingerprint = Fingerprint("review", new { formId, revision, evidence = normalizedEvidence }, mutation);
        var replay = await definitions.ReplayAsync(formId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return StateResult(replay);
        var current = await RequiredDefinitionAsync(formId, cancellationToken).ConfigureAwait(false);
        RequireExpectedVersion(mutation, current.Version);
        RequireRevisionAndState(current.Definition, revision, FormLifecycleState.Draft);
        var candidate = await compiler.CompileAsync(current.Definition, mutation.RequestedAt, cancellationToken).ConfigureAwait(false);
        RequireCandidateValid(candidate);
        var next = current.Definition with { State = FormLifecycleState.InReview };
        var persisted = await PersistAsync("review", fingerprint, next, candidate, normalizedEvidence, mutation, requireAbsent: false, cancellationToken).ConfigureAwait(false);
        return new FormMutationResult<FormLifecycleState>(persisted.Value.State, persisted.Version, persisted.WasReplay);
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormLifecycleState>> ApproveAsync(FormId formId, FormRevision revision, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, expectedVersionRequired: true);
        var fingerprint = Fingerprint("approve", new { formId, revision }, mutation);
        var replay = await definitions.ReplayAsync(formId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return StateResult(replay);
        var current = await RequiredDefinitionAsync(formId, cancellationToken).ConfigureAwait(false);
        RequireExpectedVersion(mutation, current.Version);
        RequireRevisionAndState(current.Definition, revision, FormLifecycleState.InReview);
        RequirePrepared(current);
        var persisted = await PersistAsync("approve", fingerprint, current.Definition with { State = FormLifecycleState.Approved }, current.Candidate, current.Evidence, mutation, requireAbsent: false, cancellationToken).ConfigureAwait(false);
        return new FormMutationResult<FormLifecycleState>(persisted.Value.State, persisted.Version, persisted.WasReplay);
    }

    /// <inheritdoc />
    public async ValueTask<FormMutationResult<FormRelease>> PublishAsync(FormId formId, FormRevision revision, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, expectedVersionRequired: true);
        var fingerprint = Fingerprint("publish", new { formId, revision }, mutation);
        var replay = await definitions.ReplayAsync(formId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null)
        {
            var replayedRelease = BuildRelease(replay.Snapshot, mutation);
            await releases.WriteAsync(replayedRelease, cancellationToken).ConfigureAwait(false);
            return new FormMutationResult<FormRelease>(replayedRelease, replay.Snapshot.Version, true);
        }
        var current = await RequiredDefinitionAsync(formId, cancellationToken).ConfigureAwait(false);
        RequireExpectedVersion(mutation, current.Version);
        RequireRevisionAndState(current.Definition, revision, FormLifecycleState.Approved);
        RequirePrepared(current);
        var release = BuildRelease(current, mutation);
        await releases.WriteAsync(release, cancellationToken).ConfigureAwait(false);
        var persisted = await PersistAsync("publish", fingerprint, current.Definition with { State = FormLifecycleState.Published }, current.Candidate, current.Evidence, mutation, requireAbsent: false, cancellationToken).ConfigureAwait(false);
        return new FormMutationResult<FormRelease>(release, persisted.Version, persisted.WasReplay);
    }

    /// <inheritdoc />
    public ValueTask<FormMutationResult<FormRelease>> RetireAsync(FormReleaseId releaseId, FormMutationContext mutation, CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, expectedVersionRequired: true);
        return retirements.RetireAsync(releaseId, Fingerprint("retire", releaseId, mutation), mutation, cancellationToken);
    }

    /// <summary>Persists one aggregate command and projects its public result.</summary>
    private async ValueTask<FormMutationResult<FormDefinition>> PersistAsync(string operation, string fingerprint, FormDefinition definition, FormCandidate? candidate, IReadOnlyList<string> evidence, FormMutationContext mutation, bool requireAbsent, CancellationToken cancellationToken)
    {
        var result = await definitions.WriteAsync(new FormDefinitionPersistenceCommand(operation, fingerprint, definition, candidate, evidence, mutation, requireAbsent), cancellationToken).ConfigureAwait(false);
        return DefinitionResult(result);
    }

    /// <summary>Gets one required aggregate snapshot.</summary>
    private async ValueTask<FormDefinitionSnapshot> RequiredDefinitionAsync(FormId formId, CancellationToken cancellationToken) => await definitions.GetAsync(formId, cancellationToken).ConfigureAwait(false) ?? throw new KeyNotFoundException("The form definition does not exist.");
    /// <summary>Rejects a definition containing blocking diagnostics.</summary>
    private async ValueTask RequireValidAsync(FormDefinition definition, CancellationToken cancellationToken)
    {
        var diagnostics = await validator.ValidateAsync(definition, cancellationToken).ConfigureAwait(false);
        if (diagnostics.Any(item => item.Severity == FormDiagnosticSeverity.Error)) throw new InvalidOperationException("The form definition contains blocking diagnostics.");
    }

    /// <summary>Rejects a candidate containing blocking diagnostics.</summary>
    private static void RequireCandidateValid(FormCandidate candidate)
    {
        if (candidate.Diagnostics.Any(item => item.Severity == FormDiagnosticSeverity.Error)) throw new InvalidOperationException("The compiled form candidate contains blocking diagnostics.");
    }

    /// <summary>Requires candidate and evidence bound to the current revision.</summary>
    private static void RequirePrepared(FormDefinitionSnapshot snapshot)
    {
        if (snapshot.Candidate is null || snapshot.Candidate.FormId != snapshot.Definition.Id || snapshot.Candidate.Revision != snapshot.Definition.Revision || snapshot.Evidence.Count == 0) throw new InvalidOperationException("The form revision has no matching compiled candidate and acceptance evidence.");
        RequireCandidateValid(snapshot.Candidate);
    }

    /// <summary>Bounds and normalizes acceptance-evidence references.</summary>
    private static IReadOnlyList<string> NormalizeEvidence(IReadOnlyList<string> evidence)
    {
        if (evidence.Count is < 1 or > 100) throw new InvalidOperationException("Form review requires from 1 through 100 evidence references.");
        var normalized = evidence.Select(item => item?.Trim() ?? string.Empty).ToArray();
        if (normalized.Any(item => item.Length is < 1 or > 1024)) throw new InvalidOperationException("Each form evidence reference must contain from 1 through 1024 characters.");
        if (normalized.Distinct(StringComparer.Ordinal).Count() != normalized.Length) throw new InvalidOperationException("Form evidence references must be unique.");
        return normalized;
    }

    /// <summary>Builds immutable release content from a prepared aggregate.</summary>
    private static FormRelease BuildRelease(FormDefinitionSnapshot snapshot, FormMutationContext mutation)
    {
        RequirePrepared(snapshot);
        return new FormRelease(new FormReleaseId($"{snapshot.Definition.Id.Value}-v{snapshot.Definition.Revision.Value}"), snapshot.Candidate!, mutation.RequestedAt, mutation.Actor, snapshot.Evidence.ToArray());
    }

    /// <summary>Projects a storage result as a definition mutation.</summary>
    private static FormMutationResult<FormDefinition> DefinitionResult(FormDefinitionPersistenceResult result) => new(result.Snapshot.Definition, result.Snapshot.Version, result.WasReplay);
    /// <summary>Projects a storage result as a lifecycle-state mutation.</summary>
    private static FormMutationResult<FormLifecycleState> StateResult(FormDefinitionPersistenceResult result) => new(result.Snapshot.Definition.State, result.Snapshot.Version, result.WasReplay);
    /// <summary>Requires an exact current revision.</summary>
    private static void RequireRevision(FormDefinition definition, FormRevision revision) { if (definition.Revision != revision) throw new InvalidOperationException("The form revision does not match the current definition."); }
    /// <summary>Requires an exact current revision and lifecycle state.</summary>
    private static void RequireRevisionAndState(FormDefinition definition, FormRevision revision, FormLifecycleState state) { RequireRevision(definition, revision); if (definition.State != state) throw new InvalidOperationException($"The form revision must be in the {state} state."); }
    /// <summary>Requires the caller's opaque version to match current storage.</summary>
    private static void RequireExpectedVersion(FormMutationContext mutation, FormConcurrencyToken current) { if (mutation.ExpectedVersion != current) throw new InvalidOperationException("The form definition concurrency token does not match."); }

    /// <summary>Requires complete mutation identity and explicit concurrency when applicable.</summary>
    private static void ValidateMutation(FormMutationContext mutation, bool expectedVersionRequired)
    {
        ArgumentNullException.ThrowIfNull(mutation);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.IdempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Kind);
        if (mutation.RequestedAt == default) throw new ArgumentException("A form mutation timestamp is required.", nameof(mutation));
        if (expectedVersionRequired && mutation.ExpectedVersion is null) throw new InvalidOperationException("The form mutation requires an optimistic concurrency token.");
        if (!expectedVersionRequired && mutation.ExpectedVersion is not null) throw new InvalidOperationException("A form create mutation cannot supply an existing version.");
    }

    /// <summary>Creates a stable fingerprint for one semantic command.</summary>
    private static string Fingerprint(string operation, object value, FormMutationContext mutation) => Hash(JsonSerializer.Serialize(new { operation, value, mutation.ExpectedVersion, mutation.Actor, mutation.RequestedAt, mutation.CorrelationId }, SerializerOptions));
    /// <summary>Computes a lowercase SHA-256 digest.</summary>
    private static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
