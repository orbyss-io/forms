namespace ProgramKit.Forms;

/// <summary>Represents one resumable response bound to the exact immutable form release that accepted it.</summary>
public sealed record FormDraft(
    FormDraftId Id,
    FormReleaseId ReleaseId,
    string OwnerId,
    FormDataDocument Data,
    FormDraftState State,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    FormAuditActor UpdatedBy);
