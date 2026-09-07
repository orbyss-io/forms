namespace Orbyss.Forms;

/// <summary>Supplies server-derived identity and explicit administrative reach to operational queries.</summary>
public sealed record FormRequestContext(FormAuditActor Actor, bool CanAccessAll = false);
