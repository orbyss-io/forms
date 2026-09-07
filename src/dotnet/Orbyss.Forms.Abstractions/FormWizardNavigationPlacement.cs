namespace Orbyss.Forms;

/// <summary>Controls the preferred wizard navigation placement before responsive adaptation.</summary>
public enum FormWizardNavigationPlacement
{
    /// <summary>Navigation appears above the active step.</summary>
    Top,
    /// <summary>Navigation appears beside the active step when space permits.</summary>
    Side,
    /// <summary>The renderer selects placement from the available container space.</summary>
    Adaptive
}
