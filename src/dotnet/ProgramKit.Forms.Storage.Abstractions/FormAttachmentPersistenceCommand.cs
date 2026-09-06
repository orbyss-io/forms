namespace ProgramKit.Forms;

/// <summary>Describes one durable attachment metadata mutation.</summary>
public sealed record FormAttachmentPersistenceCommand(string Operation, string Fingerprint, FormAttachment Attachment, string? ContentKey, FormMutationContext Mutation, bool RequireAbsent = false);
