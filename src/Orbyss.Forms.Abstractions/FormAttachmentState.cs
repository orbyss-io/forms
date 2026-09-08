namespace Orbyss.Forms;

/// <summary>Describes the security and lifecycle state of attachment content.</summary>
public enum FormAttachmentState
{
    /// <summary>The content is quarantined until a scanner reaches a decision.</summary>
    PendingScan,

    /// <summary>The content passed policy and malware scanning and may be consumed.</summary>
    Available,

    /// <summary>The content failed policy or malware scanning and was not promoted.</summary>
    Rejected,

    /// <summary>The owner removed the attachment from active use.</summary>
    Removed
}
