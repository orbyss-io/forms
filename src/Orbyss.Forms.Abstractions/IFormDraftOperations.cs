namespace Orbyss.Forms;

/// <summary>Creates, resumes, saves, queries, and abandons owner-scoped form drafts.</summary>
public interface IFormDraftOperations
{
    /// <summary>Creates a caller-identified draft bound to one immutable form release.</summary>
    ValueTask<FormMutationResult<FormDraft>> CreateAsync(FormDraftId draftId, FormReleaseId releaseId, string json, FormMutationContext mutation, CancellationToken cancellationToken = default);

    /// <summary>Gets a draft when the request context owns it or has administrative reach.</summary>
    ValueTask<FormDraftDocument?> GetAsync(FormDraftId draftId, FormRequestContext request, CancellationToken cancellationToken = default);

    /// <summary>Finds a bounded page of drafts visible to the request context.</summary>
    ValueTask<FormPage<FormDraftDocument>> FindDraftsAsync(FormRequestContext request, int first = 0, int maximum = 100, CancellationToken cancellationToken = default);

    /// <summary>Replaces active draft data after optimistic, idempotent and authoritative draft validation.</summary>
    ValueTask<FormMutationResult<FormDraft>> SaveAsync(FormDraftId draftId, string json, FormMutationContext mutation, CancellationToken cancellationToken = default);

    /// <summary>Marks an active draft abandoned without deleting its audit record.</summary>
    ValueTask<FormMutationResult<FormDraft>> AbandonAsync(FormDraftId draftId, FormMutationContext mutation, CancellationToken cancellationToken = default);
}
