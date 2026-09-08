namespace Orbyss.Forms;

/// <summary>Represents an opaque version used for optimistic concurrency.</summary>
public sealed record FormConcurrencyToken(string Value);
