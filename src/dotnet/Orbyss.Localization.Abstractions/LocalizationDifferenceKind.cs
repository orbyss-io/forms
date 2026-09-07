namespace Orbyss.Localization;

/// <summary>Classifies whether an immutable localization release item was added, removed, or changed.</summary>
public enum LocalizationDifferenceKind
{
    /// <summary>The item exists only in the candidate release.</summary>
    Added,
    /// <summary>The item exists only in the baseline release.</summary>
    Removed,
    /// <summary>The same stable identity has different content in the candidate release.</summary>
    Changed
}
