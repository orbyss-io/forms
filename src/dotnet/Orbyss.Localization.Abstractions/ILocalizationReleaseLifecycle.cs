namespace Orbyss.Localization;

/// <summary>Reviews, publishes, and retires governed localization releases.</summary>
public interface ILocalizationReleaseLifecycle
{
    /// <summary>Submits a validated catalog revision for review.</summary>
    ValueTask<LocalizationMutationResult<LocalizationLifecycleState>> SubmitForReviewAsync(
        LocalizationCatalogId catalogId,
        LocalizationRevision revision,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Approves a reviewed catalog revision without publishing it.</summary>
    ValueTask<LocalizationMutationResult<LocalizationLifecycleState>> ApproveAsync(
        LocalizationCatalogId catalogId,
        LocalizationRevision revision,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Creates an immutable localization release from an approved revision.</summary>
    ValueTask<LocalizationMutationResult<LocalizationRelease>> PublishAsync(
        LocalizationCatalogId catalogId,
        LocalizationRevision revision,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Retires a release while retaining its immutable messages and audit evidence.</summary>
    ValueTask<LocalizationMutationResult<LocalizationRelease>> RetireAsync(
        LocalizationReleaseId releaseId,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default);
}
