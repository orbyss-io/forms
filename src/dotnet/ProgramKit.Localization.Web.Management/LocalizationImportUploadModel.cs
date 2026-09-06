namespace ProgramKit.Localization.Web.Management;

/// <summary>Transports bounded base64 import bytes and declarative mapping metadata.</summary>
public sealed record LocalizationImportUploadModel(
    LocalizationImportFormat Format,
    string ContentBase64,
    LocalizationMergePolicy MergePolicy,
    LocalizationScope? Scope = null,
    IReadOnlyDictionary<string, string>? Mapping = null,
    string? SourceName = null,
    string? ContentSha256 = null);
