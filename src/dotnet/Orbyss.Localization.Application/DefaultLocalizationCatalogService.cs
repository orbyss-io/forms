using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Orbyss.Localization;

/// <summary>Orchestrates governed catalog authoring, imports, lifecycle, publication, queries, and retirement.</summary>
public sealed class DefaultLocalizationCatalogService :
    ILocalizationCatalogManagement,
    ILocalizationCatalogQueries,
    ILocalizationReleaseLifecycle
{
    /// <summary>Uses stable web serialization for durable command fingerprints.</summary>
    private static readonly JsonSerializerOptions SerializerOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = false
    };

    /// <summary>Persists editable catalog state and durable mutation history.</summary>
    private readonly ILocalizationCatalogStore catalogs;

    /// <summary>Persists immutable release content.</summary>
    private readonly ILocalizationReleaseStore releases;

    /// <summary>Persists mutable retirement state separately from release content.</summary>
    private readonly ILocalizationReleaseRetirementStore retirements;

    /// <summary>Validates catalogs before state transitions and persistence.</summary>
    private readonly ILocalizationCatalogValidator validator;

    /// <summary>Parses and applies hash-bound import previews.</summary>
    private readonly LocalizationImportCoordinator imports;

    /// <summary>Initializes application orchestration over explicitly selected storage providers.</summary>
    public DefaultLocalizationCatalogService(
        ILocalizationCatalogStore catalogs,
        ILocalizationReleaseStore releases,
        ILocalizationReleaseRetirementStore retirements,
        ILocalizationCatalogValidator validator,
        LocalizationImportCoordinator imports)
    {
        this.catalogs = catalogs ?? throw new ArgumentNullException(nameof(catalogs));
        this.releases = releases ?? throw new ArgumentNullException(nameof(releases));
        this.retirements = retirements ?? throw new ArgumentNullException(nameof(retirements));
        this.validator = validator ?? throw new ArgumentNullException(nameof(validator));
        this.imports = imports ?? throw new ArgumentNullException(nameof(imports));
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> CreateAsync(
        LocalizationCatalogDefinition catalog,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(catalog);
        ValidateMutation(mutation, expectedVersionRequired: false);
        var fingerprint = Fingerprint("create", catalog, mutation);
        var replay = await catalogs.ReplayAsync(catalog.Id, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return CatalogResult(replay);
        if (catalog.Revision.Value != 1 || catalog.State != LocalizationLifecycleState.Draft) throw new InvalidOperationException("A localization catalog must begin as draft revision 1.");
        await RequireValidAsync(catalog, cancellationToken).ConfigureAwait(false);
        return await PersistAsync("create", fingerprint, catalog, mutation, requireAbsent: true, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationCatalogDefinition?> GetAsync(
        LocalizationCatalogId catalogId,
        CancellationToken cancellationToken = default) =>
        (await catalogs.GetAsync(catalogId, cancellationToken).ConfigureAwait(false))?.Catalog;

    /// <inheritdoc />
    public async ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> ReplaceAsync(
        LocalizationCatalogDefinition catalog,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(catalog);
        ValidateMutation(mutation, expectedVersionRequired: true);
        var fingerprint = Fingerprint("replace", catalog, mutation);
        var replay = await catalogs.ReplayAsync(catalog.Id, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return CatalogResult(replay);
        var current = await RequiredCatalogAsync(catalog.Id, cancellationToken).ConfigureAwait(false);
        RequireExpectedVersion(mutation, current.Version);
        if (catalog.Revision.Value != current.Catalog.Revision.Value + 1 || catalog.State != LocalizationLifecycleState.Draft)
        {
            throw new InvalidOperationException("A replacement must create the next draft catalog revision.");
        }

        await RequireValidAsync(catalog, cancellationToken).ConfigureAwait(false);
        return await PersistAsync("replace", fingerprint, catalog, mutation, requireAbsent: false, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationImportPreview> PreviewImportAsync(
        LocalizationCatalogId catalogId,
        LocalizationImportRequest request,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        var current = await RequiredCatalogAsync(catalogId, cancellationToken).ConfigureAwait(false);
        return await imports.PreviewAsync(current.Catalog, request, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> ApplyImportAsync(
        LocalizationCatalogId catalogId,
        string previewId,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(previewId);
        ValidateMutation(mutation, expectedVersionRequired: true);
        var fingerprint = Fingerprint($"import:{previewId}", new { catalogId, previewId }, mutation);
        var replay = await catalogs.ReplayAsync(catalogId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return CatalogResult(replay);
        var current = await RequiredCatalogAsync(catalogId, cancellationToken).ConfigureAwait(false);
        RequireExpectedVersion(mutation, current.Version);
        var snapshotMutation = mutation with { ExpectedVersion = LocalizationImportCoordinator.CreateConcurrencyToken(current.Catalog) };
        var applied = await imports.ApplyAsync(current.Catalog, previewId, snapshotMutation, cancellationToken).ConfigureAwait(false);
        return await PersistAsync($"import:{previewId}", fingerprint, applied.Value.Catalog, mutation, requireAbsent: false, cancellationToken).ConfigureAwait(false);
    }

    /// <inheritdoc />
    public ValueTask<IReadOnlyList<LocalizationDiagnostic>> ValidateAsync(
        LocalizationCatalogDefinition catalog,
        CancellationToken cancellationToken = default) =>
        validator.ValidateAsync(catalog, cancellationToken);

    /// <inheritdoc />
    public async ValueTask<LocalizationPage<LocalizationCatalogItem>> FindAsync(
        string? search = null,
        int first = 0,
        int maximum = 100,
        CancellationToken cancellationToken = default)
    {
        if (first < 0) throw new ArgumentOutOfRangeException(nameof(first), "The localization page offset cannot be negative.");
        if (maximum is < 1 or > 1000) throw new ArgumentOutOfRangeException(nameof(maximum), "The localization page size must be from 1 through 1000.");
        var normalized = search?.Trim();
        var matches = new List<LocalizationCatalogItem>();
        await foreach (var snapshot in catalogs.FindAsync(cancellationToken).ConfigureAwait(false))
        {
            if (!string.IsNullOrEmpty(normalized)
                && !snapshot.Catalog.Id.Value.Contains(normalized, StringComparison.OrdinalIgnoreCase)
                && !snapshot.Catalog.Name.Contains(normalized, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            matches.Add(new LocalizationCatalogItem(snapshot.Catalog.Id, snapshot.Catalog.Name, snapshot.Catalog.SourceLocale, snapshot.Catalog.Revision, snapshot.Catalog.State, snapshot.Version));
        }

        var ordered = matches.OrderBy(item => item.Name, StringComparer.OrdinalIgnoreCase).ThenBy(item => item.Id.Value, StringComparer.Ordinal).ToArray();
        return new LocalizationPage<LocalizationCatalogItem>(ordered.Skip(first).Take(maximum).ToArray(), ordered.Length);
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationCatalogDocument?> GetCatalogAsync(
        LocalizationCatalogId catalogId,
        CancellationToken cancellationToken = default)
    {
        var snapshot = await catalogs.GetAsync(catalogId, cancellationToken).ConfigureAwait(false);
        return snapshot is null ? null : new LocalizationCatalogDocument(snapshot.Catalog, snapshot.Version);
    }

    /// <inheritdoc />
    public ValueTask<LocalizationRelease?> GetReleaseAsync(
        LocalizationReleaseId releaseId,
        CancellationToken cancellationToken = default) =>
        releases.GetAsync(releaseId, cancellationToken);

    /// <inheritdoc />
    public async ValueTask<LocalizationMutationResult<LocalizationLifecycleState>> SubmitForReviewAsync(
        LocalizationCatalogId catalogId,
        LocalizationRevision revision,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        var result = await TransitionAsync(catalogId, revision, LocalizationLifecycleState.Draft, LocalizationLifecycleState.InReview, "review", mutation, validate: true, cancellationToken).ConfigureAwait(false);
        return new LocalizationMutationResult<LocalizationLifecycleState>(result.Value.State, result.Version, result.WasReplay);
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationMutationResult<LocalizationLifecycleState>> ApproveAsync(
        LocalizationCatalogId catalogId,
        LocalizationRevision revision,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        var result = await TransitionAsync(catalogId, revision, LocalizationLifecycleState.InReview, LocalizationLifecycleState.Approved, "approve", mutation, validate: true, cancellationToken).ConfigureAwait(false);
        return new LocalizationMutationResult<LocalizationLifecycleState>(result.Value.State, result.Version, result.WasReplay);
    }

    /// <inheritdoc />
    public async ValueTask<LocalizationMutationResult<LocalizationRelease>> PublishAsync(
        LocalizationCatalogId catalogId,
        LocalizationRevision revision,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, expectedVersionRequired: true);
        var fingerprint = Fingerprint("publish", new { catalogId, revision }, mutation);
        var replay = await catalogs.ReplayAsync(catalogId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null)
        {
            var replayedRelease = BuildRelease(replay.Snapshot.Catalog, mutation);
            await releases.WriteAsync(replayedRelease, cancellationToken).ConfigureAwait(false);
            return new LocalizationMutationResult<LocalizationRelease>(replayedRelease, replay.Snapshot.Version, true);
        }
        var current = await RequiredCatalogAsync(catalogId, cancellationToken).ConfigureAwait(false);
        RequireExpectedVersion(mutation, current.Version);
        RequireRevisionAndState(current.Catalog, revision, LocalizationLifecycleState.Approved);
        await RequireValidAsync(current.Catalog, cancellationToken).ConfigureAwait(false);
        var release = BuildRelease(current.Catalog, mutation);
        await releases.WriteAsync(release, cancellationToken).ConfigureAwait(false);
        var published = current.Catalog with { State = LocalizationLifecycleState.Published };
        var persisted = await PersistAsync("publish", fingerprint, published, mutation, requireAbsent: false, cancellationToken).ConfigureAwait(false);
        return new LocalizationMutationResult<LocalizationRelease>(release, persisted.Version, persisted.WasReplay);
    }

    /// <inheritdoc />
    public ValueTask<LocalizationMutationResult<LocalizationRelease>> RetireAsync(
        LocalizationReleaseId releaseId,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        ValidateMutation(mutation, expectedVersionRequired: true);
        return retirements.RetireAsync(releaseId, Fingerprint("retire", releaseId, mutation), mutation, cancellationToken);
    }

    /// <summary>Applies one validated same-revision lifecycle transition.</summary>
    private async ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> TransitionAsync(
        LocalizationCatalogId catalogId,
        LocalizationRevision revision,
        LocalizationLifecycleState expected,
        LocalizationLifecycleState next,
        string operation,
        LocalizationMutationContext mutation,
        bool validate,
        CancellationToken cancellationToken)
    {
        ValidateMutation(mutation, expectedVersionRequired: true);
        var fingerprint = Fingerprint(operation, new { catalogId, revision, next }, mutation);
        var replay = await catalogs.ReplayAsync(catalogId, mutation.IdempotencyKey, fingerprint, cancellationToken).ConfigureAwait(false);
        if (replay is not null) return CatalogResult(replay);
        var current = await RequiredCatalogAsync(catalogId, cancellationToken).ConfigureAwait(false);
        RequireExpectedVersion(mutation, current.Version);
        RequireRevisionAndState(current.Catalog, revision, expected);
        if (validate) await RequireValidAsync(current.Catalog, cancellationToken).ConfigureAwait(false);
        return await PersistAsync(operation, fingerprint, current.Catalog with { State = next }, mutation, requireAbsent: false, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Persists one catalog command and projects the storage outcome.</summary>
    private async ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> PersistAsync(
        string operation,
        string fingerprint,
        LocalizationCatalogDefinition catalog,
        LocalizationMutationContext mutation,
        bool requireAbsent,
        CancellationToken cancellationToken)
    {
        var command = new LocalizationCatalogPersistenceCommand(operation, fingerprint, catalog, mutation, requireAbsent);
        var result = await catalogs.WriteAsync(command, cancellationToken).ConfigureAwait(false);
        return CatalogResult(result);
    }

    /// <summary>Projects one durable persistence outcome into the public mutation contract.</summary>
    private static LocalizationMutationResult<LocalizationCatalogDefinition> CatalogResult(LocalizationCatalogPersistenceResult result) =>
        new(result.Snapshot.Catalog, result.Snapshot.Version, result.WasReplay);

    /// <summary>Gets one required current catalog snapshot.</summary>
    private async ValueTask<LocalizationCatalogSnapshot> RequiredCatalogAsync(
        LocalizationCatalogId catalogId,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(catalogId);
        ArgumentException.ThrowIfNullOrWhiteSpace(catalogId.Value);
        return await catalogs.GetAsync(catalogId, cancellationToken).ConfigureAwait(false)
            ?? throw new KeyNotFoundException("The localization catalog does not exist.");
    }

    /// <summary>Rejects a catalog containing any blocking semantic diagnostic.</summary>
    private async ValueTask RequireValidAsync(
        LocalizationCatalogDefinition catalog,
        CancellationToken cancellationToken)
    {
        var diagnostics = await validator.ValidateAsync(catalog, cancellationToken).ConfigureAwait(false);
        var errors = diagnostics.Where(item => item.Severity == LocalizationDiagnosticSeverity.Error).ToArray();
        if (errors.Length > 0) throw new InvalidOperationException($"The localization catalog has {errors.Length} blocking diagnostic(s): {string.Join(", ", errors.Select(item => item.Code))}.");
    }

    /// <summary>Requires the exact revision and lifecycle predecessor.</summary>
    private static void RequireRevisionAndState(
        LocalizationCatalogDefinition catalog,
        LocalizationRevision revision,
        LocalizationLifecycleState expected)
    {
        if (catalog.Revision != revision) throw new InvalidOperationException("The requested localization revision is not current.");
        if (catalog.State != expected) throw new InvalidOperationException($"Localization revision {revision.Value} must be {expected} for this transition.");
    }

    /// <summary>Performs an early opaque-version check while storage retains the final atomic check.</summary>
    private static void RequireExpectedVersion(
        LocalizationMutationContext mutation,
        LocalizationConcurrencyToken current)
    {
        if (mutation.ExpectedVersion is null || !string.Equals(mutation.ExpectedVersion.Value, current.Value, StringComparison.Ordinal))
        {
            throw new InvalidOperationException("The localization catalog concurrency token does not match.");
        }
    }

    /// <summary>Builds deterministic immutable content from approved values and required locale policy.</summary>
    private static LocalizationRelease BuildRelease(
        LocalizationCatalogDefinition catalog,
        LocalizationMutationContext mutation)
    {
        var locales = catalog.Locales.ToDictionary(item => item.LanguageTag, StringComparer.OrdinalIgnoreCase);
        var source = locales[catalog.SourceLocale];
        var entries = new List<LocalizationReleaseEntry>();
        foreach (var message in catalog.Messages.OrderBy(item => ScopeIdentity(item.Scope), StringComparer.Ordinal).ThenBy(item => item.Key, StringComparer.Ordinal))
        {
            entries.Add(new LocalizationReleaseEntry(message.Key, message.Scope, catalog.SourceLocale, source.Direction, message.SourcePattern, message.Arguments));
            foreach (var locale in catalog.Locales.Where(item => !string.Equals(item.LanguageTag, catalog.SourceLocale, StringComparison.OrdinalIgnoreCase)))
            {
                var value = message.Values.SingleOrDefault(item => string.Equals(item.LanguageTag, locale.LanguageTag, StringComparison.OrdinalIgnoreCase) && item.State == LocalizationValueState.Approved);
                if (value is null)
                {
                    if (locale.RequiredForPublication) throw new InvalidOperationException($"Required locale '{locale.LanguageTag}' has no approved value for '{message.Key}'.");
                    continue;
                }

                entries.Add(new LocalizationReleaseEntry(message.Key, message.Scope, locale.LanguageTag, locale.Direction, value.Pattern, message.Arguments));
            }
        }

        var orderedEntries = entries.OrderBy(item => ScopeIdentity(item.Scope), StringComparer.Ordinal).ThenBy(item => item.Key, StringComparer.Ordinal).ThenBy(item => item.LanguageTag, StringComparer.OrdinalIgnoreCase).ToArray();
        var releaseId = new LocalizationReleaseId($"{catalog.Id.Value}-v{catalog.Revision.Value}");
        var content = new { releaseId, catalog.Id, catalog.Revision, catalog.SourceLocale, catalog.Locales, Entries = orderedEntries };
        var sha256 = Hash(JsonSerializer.Serialize(content, SerializerOptions));
        return new LocalizationRelease(releaseId, catalog.Id, catalog.Revision, catalog.SourceLocale, catalog.Locales, orderedEntries, sha256, mutation.RequestedAt, mutation.Actor);
    }

    /// <summary>Requires complete mutation identity and explicit concurrency where applicable.</summary>
    private static void ValidateMutation(LocalizationMutationContext mutation, bool expectedVersionRequired)
    {
        ArgumentNullException.ThrowIfNull(mutation);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.IdempotencyKey);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Id);
        ArgumentException.ThrowIfNullOrWhiteSpace(mutation.Actor.Kind);
        if (mutation.RequestedAt == default) throw new ArgumentException("A localization mutation timestamp is required.", nameof(mutation));
        if (expectedVersionRequired && mutation.ExpectedVersion is null) throw new InvalidOperationException("The localization mutation requires an optimistic concurrency token.");
        if (!expectedVersionRequired && mutation.ExpectedVersion is not null) throw new InvalidOperationException("A localization create mutation cannot supply an existing version.");
    }

    /// <summary>Creates a durable idempotency fingerprint for one semantic command.</summary>
    private static string Fingerprint(string operation, object value, LocalizationMutationContext mutation) =>
        Hash(JsonSerializer.Serialize(new { operation, value, mutation.ExpectedVersion, mutation.Actor, mutation.RequestedAt, mutation.CorrelationId }, SerializerOptions));

    /// <summary>Creates a stable structured-scope identity.</summary>
    private static string ScopeIdentity(LocalizationScope scope) =>
        $"{scope.Kind}:{scope.ParentResourceId}:{scope.ResourceId}";

    /// <summary>Computes a lowercase SHA-256 digest.</summary>
    private static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
