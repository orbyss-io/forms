namespace ProgramKit.Forms;

/// <summary>Describes a layout element independently from a renderer library.</summary>
public enum FormElementKind
{
    /// <summary>Renders a field control.</summary>
    Control,
    /// <summary>Groups related child elements.</summary>
    Group,
    /// <summary>Places child elements in a responsive row when space permits.</summary>
    HorizontalLayout,
    /// <summary>Places child elements in document order.</summary>
    VerticalLayout,
    /// <summary>Hosts governed multi-step navigation.</summary>
    Wizard,
    /// <summary>Defines one wizard step.</summary>
    Step,
    /// <summary>Renders non-executable explanatory text.</summary>
    Text,
    /// <summary>Hosts allowlisted form actions.</summary>
    ActionBar
}
