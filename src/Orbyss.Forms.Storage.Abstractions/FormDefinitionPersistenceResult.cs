namespace Orbyss.Forms;

/// <summary>Returns the exact form-definition result originally bound to a durable command key.</summary>
public sealed record FormDefinitionPersistenceResult(FormDefinitionSnapshot Snapshot, bool WasReplay);
