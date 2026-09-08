namespace Orbyss.Forms;

/// <summary>Describes attachment metadata without exposing quarantined bytes or a storage locator.</summary>
public sealed record FormAttachment(
    FormAttachmentId Id,
    FormDraftId DraftId,
    string OwnerId,
    string FileName,
    string MediaType,
    long Length,
    string Sha256,
    FormAttachmentState State,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    FormAuditActor UpdatedBy,
    string? RejectionCode = null);
