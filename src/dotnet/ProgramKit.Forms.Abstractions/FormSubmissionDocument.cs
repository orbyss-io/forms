namespace ProgramKit.Forms;

/// <summary>Pairs a submission with its opaque optimistic-concurrency version.</summary>
public sealed record FormSubmissionDocument(FormSubmission Submission, FormConcurrencyToken Version);
