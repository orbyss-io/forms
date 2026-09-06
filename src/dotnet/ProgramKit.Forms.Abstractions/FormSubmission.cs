namespace ProgramKit.Forms;

/// <summary>Represents an immutable response snapshot and its auditable processing state.</summary>
public sealed record FormSubmission(
    FormSubmissionId Id,
    FormDraftId DraftId,
    FormReleaseId ReleaseId,
    string OwnerId,
    FormDataDocument Data,
    IReadOnlyList<FormAttachmentId> AttachmentIds,
    FormSubmissionState State,
    DateTimeOffset SubmittedAt,
    FormAuditActor SubmittedBy,
    DateTimeOffset UpdatedAt,
    FormAuditActor UpdatedBy,
    string? DecisionReason = null);
