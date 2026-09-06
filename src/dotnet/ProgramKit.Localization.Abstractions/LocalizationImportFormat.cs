namespace ProgramKit.Localization;

/// <summary>Identifies a supported localization interchange representation.</summary>
public enum LocalizationImportFormat
{
    /// <summary>Comma-separated values with an explicit mapping.</summary>
    Csv,
    /// <summary>An Excel workbook with an explicit sheet and column mapping.</summary>
    Xlsx,
    /// <summary>A bounded Program Kit JSON interchange document.</summary>
    Json,
    /// <summary>An OASIS XLIFF 2.1 document.</summary>
    Xliff21,
    /// <summary>A GNU gettext portable object document.</summary>
    Po
}
