namespace ProgramKit.Localization;

/// <summary>Describes the governed lifecycle state of a localization catalog revision.</summary>
public enum LocalizationLifecycleState
{
    /// <summary>The catalog revision is editable.</summary>
    Draft,
    /// <summary>The catalog revision has passed semantic validation.</summary>
    Validated,
    /// <summary>The catalog revision is awaiting an authorized review decision.</summary>
    InReview,
    /// <summary>The catalog revision was approved for publication.</summary>
    Approved,
    /// <summary>The catalog revision is available as an immutable runtime release.</summary>
    Published,
    /// <summary>The release is retained but no longer offered for new use.</summary>
    Retired
}
