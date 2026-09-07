namespace Orbyss.Forms;

/// <summary>Describes the governed lifecycle state of a form revision.</summary>
public enum FormLifecycleState
{
    /// <summary>The revision is editable.</summary>
    Draft,
    /// <summary>The revision has passed semantic validation.</summary>
    Validated,
    /// <summary>The revision has deterministic compiled artifacts.</summary>
    Compiled,
    /// <summary>The compiled artifacts have required acceptance evidence.</summary>
    Tested,
    /// <summary>The revision is awaiting an authorized review decision.</summary>
    InReview,
    /// <summary>The revision was approved for publication.</summary>
    Approved,
    /// <summary>The revision is available as an immutable runtime release.</summary>
    Published,
    /// <summary>The release is retained but no longer offered for new use.</summary>
    Retired
}
