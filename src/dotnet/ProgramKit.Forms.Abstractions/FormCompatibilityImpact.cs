namespace ProgramKit.Forms;

/// <summary>Describes how a form change affects existing consumers or saved data.</summary>
public enum FormCompatibilityImpact
{
    /// <summary>The change does not affect existing consumers.</summary>
    Compatible,
    /// <summary>The change may require consumer review without a mandatory migration.</summary>
    Review,
    /// <summary>The change requires an explicit consumer or saved-data migration.</summary>
    Breaking
}
