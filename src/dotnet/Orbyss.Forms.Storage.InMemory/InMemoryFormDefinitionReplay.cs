namespace Orbyss.Forms;

/// <summary>Binds one idempotency key to its fingerprint and historical result.</summary>
internal sealed record InMemoryFormDefinitionReplay(string Fingerprint, FormDefinitionSnapshot Snapshot);
