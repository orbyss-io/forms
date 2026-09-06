namespace ProgramKit.Localization;

/// <summary>Supplies bounded untrusted import content and an explicit mapping policy.</summary>
public sealed record LocalizationImportRequest(
    LocalizationImportFormat Format,
    ReadOnlyMemory<byte> Content,
    LocalizationMergePolicy MergePolicy,
    LocalizationScope? Scope = null,
    IReadOnlyDictionary<string, string>? Mapping = null,
    string? SourceName = null,
    string? ContentSha256 = null);
