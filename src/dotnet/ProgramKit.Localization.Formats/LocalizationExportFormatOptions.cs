namespace ProgramKit.Localization.Formats;

/// <summary>Bounds generated localization documents before they leave the export boundary.</summary>
public sealed record LocalizationExportFormatOptions(
    int MaximumContentBytes = 8 * 1024 * 1024,
    int MaximumRows = 20_000,
    int MaximumColumns = 128,
    int MaximumCellCharacters = 16_384);
