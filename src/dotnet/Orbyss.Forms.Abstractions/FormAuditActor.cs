namespace Orbyss.Forms;

/// <summary>Identifies the human, service, or governed tool requesting a form mutation.</summary>
public sealed record FormAuditActor(string Id, string Kind, string? DisplayName = null);
