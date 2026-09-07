namespace Orbyss.Localization;

/// <summary>Contains the deterministic locale-policy and message changes between two releases.</summary>
public sealed record LocalizationReleaseDifference(
    LocalizationReleaseId BaselineReleaseId,
    LocalizationReleaseId CandidateReleaseId,
    bool SourceLocaleChanged,
    IReadOnlyList<LocalizationLocaleDifference> LocaleDifferences,
    IReadOnlyList<LocalizationEntryDifference> EntryDifferences)
{
    /// <summary>Gets whether the candidate differs from the baseline.</summary>
    public bool HasChanges => SourceLocaleChanged || LocaleDifferences.Count > 0 || EntryDifferences.Count > 0;
}
