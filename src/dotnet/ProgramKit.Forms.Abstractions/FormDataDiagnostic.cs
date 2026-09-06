namespace ProgramKit.Forms;

/// <summary>Reports one public-safe issue in submitted data.</summary>
public sealed record FormDataDiagnostic(
    string Code,
    FormDiagnosticSeverity Severity,
    string Message,
    string DataPath);
