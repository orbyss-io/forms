namespace ProgramKit.Forms;

/// <summary>Describes one durable, optimistic and idempotent aggregate mutation.</summary>
public sealed record FormSubmissionPersistenceCommand(string Operation, string Fingerprint, FormDraft Draft, FormSubmission? Submission, FormMutationContext Mutation, bool RequireAbsent = false);
