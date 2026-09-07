namespace Orbyss.Localization;

/// <summary>Describes how a localization diagnostic affects import or publication.</summary>
public enum LocalizationDiagnosticSeverity
{
    /// <summary>Advisory information that does not block progress.</summary>
    Information,
    /// <summary>A concern that should be reviewed but does not itself block progress.</summary>
    Warning,
    /// <summary>A defect that blocks the governed transition.</summary>
    Error
}
