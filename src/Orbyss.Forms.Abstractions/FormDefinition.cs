namespace Orbyss.Forms;

/// <summary>Represents an editable, provider-neutral form revision.</summary>
public sealed record FormDefinition(
    FormId Id,
    FormRevision Revision,
    string Name,
    string SourceLocale,
    FormLifecycleState State,
    IReadOnlyList<FormFieldDefinition> Fields,
    FormElementDefinition Layout,
    IReadOnlyList<FormActionReference> Actions,
    IReadOnlyDictionary<string, string>? Metadata = null);
