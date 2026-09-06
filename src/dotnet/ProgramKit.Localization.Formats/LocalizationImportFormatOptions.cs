namespace ProgramKit.Localization.Formats;

/// <summary>Bounds untrusted localization interchange documents and archive expansion.</summary>
public sealed record LocalizationImportFormatOptions(
    int MaximumContentBytes = 8 * 1024 * 1024,
    int MaximumExpandedBytes = 32 * 1024 * 1024,
    int MaximumArchiveEntries = 128,
    int MaximumRows = 20_000,
    int MaximumColumns = 128,
    int MaximumCellCharacters = 16_384);
