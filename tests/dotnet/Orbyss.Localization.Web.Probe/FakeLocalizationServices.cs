using Orbyss.Localization;

/// <summary>Records web-boundary calls while returning stable provider-neutral fixtures.</summary>
internal sealed class FakeLocalizationServices(
    LocalizationCatalogDefinition catalog,
    LocalizationRelease release) : ILocalizationCatalogManagement, ILocalizationCatalogQueries, ILocalizationReleaseLifecycle
{
    /// <summary>Gets the last mutation received through an authenticated endpoint.</summary>
    public LocalizationMutationContext? LastMutation { get; private set; }

    /// <inheritdoc />
    public ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> CreateAsync(LocalizationCatalogDefinition value, LocalizationMutationContext mutation, CancellationToken cancellationToken = default) => Result(value, mutation);

    /// <inheritdoc />
    public ValueTask<LocalizationCatalogDefinition?> GetAsync(LocalizationCatalogId catalogId, CancellationToken cancellationToken = default) => ValueTask.FromResult<LocalizationCatalogDefinition?>(catalogId == catalog.Id ? catalog : null);

    /// <inheritdoc />
    public ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> ReplaceAsync(LocalizationCatalogDefinition value, LocalizationMutationContext mutation, CancellationToken cancellationToken = default) => Result(value, mutation);

    /// <inheritdoc />
    public ValueTask<LocalizationImportPreview> PreviewImportAsync(LocalizationCatalogId catalogId, LocalizationImportRequest request, CancellationToken cancellationToken = default) => ValueTask.FromResult(new LocalizationImportPreview("preview", new string('a', 64), catalog.Revision, request.MergePolicy, [], []));

    /// <inheritdoc />
    public ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> ApplyImportAsync(LocalizationCatalogId catalogId, string previewId, LocalizationMutationContext mutation, CancellationToken cancellationToken = default) => Result(catalog, mutation);

    /// <inheritdoc />
    public ValueTask<IReadOnlyList<LocalizationDiagnostic>> ValidateAsync(LocalizationCatalogDefinition value, CancellationToken cancellationToken = default) => ValueTask.FromResult<IReadOnlyList<LocalizationDiagnostic>>([]);

    /// <inheritdoc />
    public ValueTask<LocalizationPage<LocalizationCatalogItem>> FindAsync(string? search = null, int first = 0, int maximum = 100, CancellationToken cancellationToken = default) => ValueTask.FromResult(new LocalizationPage<LocalizationCatalogItem>([new LocalizationCatalogItem(catalog.Id, catalog.Name, catalog.SourceLocale, catalog.Revision, catalog.State, new LocalizationConcurrencyToken("v1"))], 1));

    /// <inheritdoc />
    public ValueTask<LocalizationCatalogDocument?> GetCatalogAsync(LocalizationCatalogId catalogId, CancellationToken cancellationToken = default) => ValueTask.FromResult<LocalizationCatalogDocument?>(catalogId == catalog.Id ? new LocalizationCatalogDocument(catalog, new LocalizationConcurrencyToken("v1")) : null);

    /// <inheritdoc />
    public ValueTask<LocalizationRelease?> GetReleaseAsync(LocalizationReleaseId releaseId, CancellationToken cancellationToken = default) => ValueTask.FromResult<LocalizationRelease?>(releaseId == release.Id ? release : null);

    /// <inheritdoc />
    public ValueTask<LocalizationMutationResult<LocalizationLifecycleState>> SubmitForReviewAsync(LocalizationCatalogId catalogId, LocalizationRevision revision, LocalizationMutationContext mutation, CancellationToken cancellationToken = default) => Result(LocalizationLifecycleState.InReview, mutation);

    /// <inheritdoc />
    public ValueTask<LocalizationMutationResult<LocalizationLifecycleState>> ApproveAsync(LocalizationCatalogId catalogId, LocalizationRevision revision, LocalizationMutationContext mutation, CancellationToken cancellationToken = default) => Result(LocalizationLifecycleState.Approved, mutation);

    /// <inheritdoc />
    public ValueTask<LocalizationMutationResult<LocalizationRelease>> PublishAsync(LocalizationCatalogId catalogId, LocalizationRevision revision, LocalizationMutationContext mutation, CancellationToken cancellationToken = default) => Result(release, mutation);

    /// <inheritdoc />
    public ValueTask<LocalizationMutationResult<LocalizationRelease>> RetireAsync(LocalizationReleaseId releaseId, LocalizationMutationContext mutation, CancellationToken cancellationToken = default) => Result(release with { Retired = true }, mutation);

    /// <summary>Records a mutation and wraps one fixture result.</summary>
    private ValueTask<LocalizationMutationResult<T>> Result<T>(T value, LocalizationMutationContext mutation)
    {
        LastMutation = mutation;
        return ValueTask.FromResult(new LocalizationMutationResult<T>(value, new LocalizationConcurrencyToken("v2"), false));
    }
}
