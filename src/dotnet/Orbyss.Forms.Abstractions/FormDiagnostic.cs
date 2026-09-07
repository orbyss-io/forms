namespace Orbyss.Forms;

/// <summary>Reports a stable machine-readable form validation or compilation finding.</summary>
public sealed record FormDiagnostic(
    string Code,
    FormDiagnosticSeverity Severity,
    string Message,
    string? Path = null);
