namespace ProgramKit.Forms;

/// <summary>Compiles, reviews, publishes, and retires governed form releases.</summary>
public interface IFormReleaseLifecycle
{
    /// <summary>Compiles one stored revision into deterministic candidate artifacts.</summary>
    ValueTask<FormCandidate> CompileAsync(
        FormId formId,
        FormRevision revision,
        CancellationToken cancellationToken = default);

    /// <summary>Records required acceptance evidence and submits the candidate for review.</summary>
    ValueTask<FormMutationResult<FormLifecycleState>> SubmitForReviewAsync(
        FormId formId,
        FormRevision revision,
        IReadOnlyList<string> evidence,
        FormMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Approves a reviewed candidate without publishing it.</summary>
    ValueTask<FormMutationResult<FormLifecycleState>> ApproveAsync(
        FormId formId,
        FormRevision revision,
        FormMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Creates an immutable release from an approved candidate.</summary>
    ValueTask<FormMutationResult<FormRelease>> PublishAsync(
        FormId formId,
        FormRevision revision,
        FormMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Retires a published release while retaining its immutable evidence.</summary>
    ValueTask<FormMutationResult<FormRelease>> RetireAsync(
        FormReleaseId releaseId,
        FormMutationContext mutation,
        CancellationToken cancellationToken = default);
}
