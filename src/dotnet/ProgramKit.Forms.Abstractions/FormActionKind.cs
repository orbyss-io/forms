namespace ProgramKit.Forms;

/// <summary>Describes the intent of an allowlisted form action.</summary>
public enum FormActionKind
{
    /// <summary>Moves to the previous visible step.</summary>
    Back,
    /// <summary>Validates the active step and advances.</summary>
    Next,
    /// <summary>Persists an incomplete resumable draft.</summary>
    SaveDraft,
    /// <summary>Skips an optional step.</summary>
    Skip,
    /// <summary>Cancels the current journey.</summary>
    Cancel,
    /// <summary>Submits the completed form.</summary>
    Submit,
    /// <summary>Invokes an application-owned typed action.</summary>
    Custom
}
