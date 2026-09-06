namespace ProgramKit.Forms;

/// <summary>Defines the internal persisted draft/submission envelope payload.</summary>
internal sealed record FormResponseDocument(FormDraft Draft, FormSubmission? Submission, string Version, IReadOnlyList<FormOperationalAuditEntry> Audit, IReadOnlyList<FormResponseCommand> Commands);
