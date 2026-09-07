namespace Orbyss.Forms;

/// <summary>Describes how a form diagnostic affects compilation or publication.</summary>
public enum FormDiagnosticSeverity
{
    /// <summary>Advisory information that does not block progress.</summary>
    Information,
    /// <summary>A concern that should be reviewed but does not itself block progress.</summary>
    Warning,
    /// <summary>A defect that blocks the governed transition.</summary>
    Error
}
