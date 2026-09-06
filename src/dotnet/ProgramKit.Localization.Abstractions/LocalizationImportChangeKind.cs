namespace ProgramKit.Localization;

/// <summary>Describes a proposed catalog effect from a parsed import.</summary>
public enum LocalizationImportChangeKind
{
    /// <summary>A new message or locale value will be created.</summary>
    Add,
    /// <summary>An existing value will be replaced.</summary>
    Replace,
    /// <summary>An existing value will remain unchanged.</summary>
    Preserve,
    /// <summary>An existing value will be removed by an explicit replacement policy.</summary>
    Remove,
    /// <summary>The proposed value conflicts with catalog state and requires a decision.</summary>
    Conflict
}
