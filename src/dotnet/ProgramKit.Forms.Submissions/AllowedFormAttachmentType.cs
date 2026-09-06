namespace ProgramKit.Forms;

/// <summary>Binds one normalized media type to allowed extensions and required leading signatures.</summary>
public sealed record AllowedFormAttachmentType(string MediaType, IReadOnlyList<string> Extensions, IReadOnlyList<ReadOnlyMemory<byte>> Signatures);
