namespace Orbyss.Forms;

/// <summary>Selects a token-driven wizard progress-line treatment.</summary>
public enum FormWizardProgressStyle
{
    /// <summary>A continuous neutral connector.</summary>
    Line,
    /// <summary>A connector filled according to progress.</summary>
    Progress,
    /// <summary>Separate connectors distinguish each step.</summary>
    Segmented,
    /// <summary>No connector is rendered.</summary>
    None
}
