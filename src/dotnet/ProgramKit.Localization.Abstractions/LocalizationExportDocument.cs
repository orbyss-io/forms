namespace ProgramKit.Localization;

/// <summary>Contains bounded exported bytes and their delivery metadata and digest.</summary>
public sealed record LocalizationExportDocument(
    LocalizationImportFormat Format,
    ReadOnlyMemory<byte> Content,
    string MediaType,
    string SuggestedFileName,
    string ContentSha256);
