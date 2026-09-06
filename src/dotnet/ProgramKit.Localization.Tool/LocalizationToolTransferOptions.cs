namespace ProgramKit.Localization.Tool;

/// <summary>Bounds localization bytes transferred through structured tool calls.</summary>
public sealed record LocalizationToolTransferOptions(int MaximumImportBytes = 8 * 1024 * 1024, int MaximumExportBytes = 8 * 1024 * 1024);
