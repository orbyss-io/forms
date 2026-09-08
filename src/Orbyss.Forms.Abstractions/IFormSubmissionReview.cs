namespace Orbyss.Forms;

/// <summary>Provides the separately authorized application-side submission decision capability.</summary>
public interface IFormSubmissionReview
{
    /// <summary>Accepts or rejects a pending submission with a public-safe reason.</summary>
    ValueTask<FormMutationResult<FormSubmission>> DecideAsync(FormSubmissionId submissionId, bool accept, string? reason, FormMutationContext mutation, CancellationToken cancellationToken = default);
}
