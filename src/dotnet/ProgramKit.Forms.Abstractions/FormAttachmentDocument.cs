namespace ProgramKit.Forms;

/// <summary>Pairs attachment metadata with its opaque optimistic-concurrency version.</summary>
public sealed record FormAttachmentDocument(FormAttachment Attachment, FormConcurrencyToken Version);
