namespace Orbyss.Localization.Tool;

/// <summary>Returns one bounded localization export through MCP-safe base64 content.</summary>
public sealed record LocalizationToolExport(LocalizationImportFormat Format, string ContentBase64, string MediaType, string SuggestedFileName, string ContentSha256);
