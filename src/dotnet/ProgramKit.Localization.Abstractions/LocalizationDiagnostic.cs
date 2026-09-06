namespace ProgramKit.Localization;

/// <summary>Reports a stable machine-readable localization validation or import finding.</summary>
public sealed record LocalizationDiagnostic(
    string Code,
    LocalizationDiagnosticSeverity Severity,
    string Message,
    string? Key = null,
    string? LanguageTag = null);
