namespace ProgramKit.Forms;

/// <summary>Returns one editable form definition with its opaque optimistic-concurrency version.</summary>
public sealed record FormDefinitionDocument(FormDefinition Definition, FormConcurrencyToken Version);
