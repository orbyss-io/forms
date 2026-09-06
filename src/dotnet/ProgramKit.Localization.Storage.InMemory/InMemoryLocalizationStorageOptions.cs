namespace ProgramKit.Localization;

/// <summary>Bounds process-local Localization persistence.</summary>
public sealed record InMemoryLocalizationStorageOptions
{
    /// <summary>Maximum catalog or release count per store.</summary>
    public int MaximumDocuments { get; init; } = 10_000;
    /// <summary>Maximum mutation/replay history retained per catalog.</summary>
    public int MaximumCommandsPerCatalog { get; init; } = 10_000;
    /// <summary>Maximum serialized UTF-8 bytes for one catalog or release.</summary>
    public int MaximumDocumentBytes { get; init; } = 16 * 1024 * 1024;
}
