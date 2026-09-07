namespace Orbyss.Forms;

/// <summary>Contains current form-definition state and exact process-local replay records.</summary>
internal sealed record InMemoryFormDefinitionDocument(FormDefinitionSnapshot Snapshot, IReadOnlyDictionary<string, InMemoryFormDefinitionReplay> Commands);
