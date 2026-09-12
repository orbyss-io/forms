namespace Orbyss.Forms;

/// <summary>Defines one stable field in the provider-neutral form data model.</summary>
public sealed record FormFieldDefinition(
    string Id,
    string DataPath,
    FormValueKind ValueKind,
    bool Required,
    LocalizedTextReference Label,
    LocalizedTextReference? Description = null,
    FormConstraints? Constraints = null,
    FormComponentReference? Component = null,
    [property: System.Text.Json.Serialization.JsonIgnore(Condition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull)] FormCondition? RequiredWhen = null,
    [property: System.Text.Json.Serialization.JsonIgnore(Condition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingDefault)] bool ReadOnly = false);
