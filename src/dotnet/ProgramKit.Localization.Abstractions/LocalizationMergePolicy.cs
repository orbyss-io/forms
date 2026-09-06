namespace ProgramKit.Localization;

/// <summary>Controls how an accepted import preview affects existing catalog values.</summary>
public enum LocalizationMergePolicy
{
    /// <summary>Rejects every key or locale value that already exists.</summary>
    AddOnly,
    /// <summary>Adds missing data and preserves every existing value.</summary>
    PreserveExisting,
    /// <summary>Replaces values present in the import while preserving unrelated data.</summary>
    ReplaceImported,
    /// <summary>Replaces the selected scope after explicit destructive review.</summary>
    ReplaceScope
}
