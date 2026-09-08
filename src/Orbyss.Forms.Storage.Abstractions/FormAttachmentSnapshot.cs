namespace Orbyss.Forms;

/// <summary>Contains attachment metadata, an opaque provider key and optimistic version.</summary>
public sealed record FormAttachmentSnapshot(FormAttachment Attachment, string? ContentKey, FormConcurrencyToken Version);
