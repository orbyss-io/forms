namespace Orbyss.Forms;

/// <summary>Contains the current draft, optional submission and opaque aggregate version.</summary>
public sealed record FormSubmissionAggregateSnapshot(FormDraft Draft, FormSubmission? Submission, FormConcurrencyToken Version, IReadOnlyList<FormOperationalAuditEntry> Audit);
