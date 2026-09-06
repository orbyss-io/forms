namespace ProgramKit.Forms;

/// <summary>Submits drafts and provides owner-scoped submission retrieval and withdrawal.</summary>
public interface IFormSubmissionOperations
{
    /// <summary>Validates and snapshots an active draft with explicitly selected clean attachments.</summary>
    ValueTask<FormMutationResult<FormSubmission>> SubmitAsync(FormDraftId draftId, IReadOnlyList<FormAttachmentId> attachmentIds, FormMutationContext mutation, CancellationToken cancellationToken = default);

    /// <summary>Gets a submission when the request context owns it or has administrative reach.</summary>
    ValueTask<FormSubmissionDocument?> GetAsync(FormSubmissionId submissionId, FormRequestContext request, CancellationToken cancellationToken = default);

    /// <summary>Finds a bounded page of submissions visible to the request context.</summary>
    ValueTask<FormPage<FormSubmissionDocument>> FindSubmissionsAsync(FormRequestContext request, int first = 0, int maximum = 100, CancellationToken cancellationToken = default);

    /// <summary>Withdraws a submitted response without deleting its immutable payload or audit record.</summary>
    ValueTask<FormMutationResult<FormSubmission>> WithdrawAsync(FormSubmissionId submissionId, FormMutationContext mutation, CancellationToken cancellationToken = default);
}
