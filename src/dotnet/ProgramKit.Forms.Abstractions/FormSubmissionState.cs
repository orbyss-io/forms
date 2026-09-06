namespace ProgramKit.Forms;

/// <summary>Describes the consumer-neutral lifecycle of a submitted form response.</summary>
public enum FormSubmissionState
{
    /// <summary>The response awaits application processing.</summary>
    Submitted,

    /// <summary>An authorized application workflow accepted the response.</summary>
    Accepted,

    /// <summary>An authorized application workflow rejected the response.</summary>
    Rejected,

    /// <summary>The owner withdrew the response before a final decision.</summary>
    Withdrawn
}
