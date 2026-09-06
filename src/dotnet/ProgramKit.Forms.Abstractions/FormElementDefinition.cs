namespace ProgramKit.Forms;

/// <summary>Defines one node in a provider-neutral form layout tree.</summary>
public sealed record FormElementDefinition(
    string Id,
    FormElementKind Kind,
    IReadOnlyList<FormElementDefinition> Elements,
    string? FieldId = null,
    LocalizedTextReference? Text = null,
    FormIconReference? Icon = null,
    FormVisibilityCondition? Visibility = null,
    FormWizardOptions? Wizard = null,
    IReadOnlyDictionary<string, string>? Presentation = null,
    FormActionBarOptions? ActionBar = null);
