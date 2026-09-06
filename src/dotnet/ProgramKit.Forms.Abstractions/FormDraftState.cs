namespace ProgramKit.Forms;

/// <summary>Describes whether a resumable form draft may still be changed.</summary>
public enum FormDraftState
{
    /// <summary>The owner may continue editing the draft.</summary>
    Active,

    /// <summary>The draft produced an immutable submission and cannot be edited.</summary>
    Submitted,

    /// <summary>The owner intentionally abandoned the draft.</summary>
    Abandoned
}
