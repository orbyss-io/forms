namespace Orbyss.Localization;

/// <summary>Compares immutable localization releases without depending on a UI or storage provider.</summary>
public interface ILocalizationReleaseDiffer
{
    /// <summary>Returns a deterministic semantic difference from baseline to candidate.</summary>
    ValueTask<LocalizationReleaseDifference> CompareAsync(
        LocalizationRelease baseline,
        LocalizationRelease candidate,
        CancellationToken cancellationToken = default);
}
