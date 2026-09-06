namespace ProgramKit.Forms;

/// <summary>References an application-registered action through a stable contract identifier.</summary>
public sealed record FormActionReference(
    string Id,
    FormActionKind Kind,
    LocalizedTextReference Label,
    string HandlerId,
    bool RequiresValidForm = false,
    FormIconReference? Icon = null);
