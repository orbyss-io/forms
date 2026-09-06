namespace ProgramKit.Forms;

/// <summary>Defines one stable field in the provider-neutral form data model.</summary>
public sealed record FormFieldDefinition(
    string Id,
    string DataPath,
    FormValueKind ValueKind,
    bool Required,
    LocalizedTextReference Label,
    LocalizedTextReference? Description = null,
    FormConstraints? Constraints = null,
    FormComponentReference? Component = null);
