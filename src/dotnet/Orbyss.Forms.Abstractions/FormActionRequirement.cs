namespace Orbyss.Forms;

/// <summary>Declares a fully described application action required by a compiled form release.</summary>
public sealed record FormActionRequirement(
    string ActionId,
    string HandlerId,
    FormActionKind Kind,
    LocalizedTextReference Label,
    bool RequiresValidForm,
    FormIconReference? Icon = null);
