namespace ProgramKit.Localization;

/// <summary>Persists mutable retirement state separately from immutable localization release content.</summary>
public interface ILocalizationReleaseRetirementStore
{
    /// <summary>Retires one release through an optimistic and durably idempotent mutation.</summary>
    ValueTask<LocalizationMutationResult<LocalizationRelease>> RetireAsync(
        LocalizationReleaseId releaseId,
        string fingerprint,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default);
}
