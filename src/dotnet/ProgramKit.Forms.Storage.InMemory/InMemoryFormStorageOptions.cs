namespace ProgramKit.Forms;

/// <summary>Bounds process-local Forms persistence.</summary>
public sealed record InMemoryFormStorageOptions
{
    /// <summary>Maximum aggregate count per in-memory store.</summary>
    public int MaximumDocuments { get; init; } = 10_000;
    /// <summary>Maximum mutation/replay history per aggregate.</summary>
    public int MaximumCommandsPerDocument { get; init; } = 10_000;
    /// <summary>Maximum serialized UTF-8 bytes for one aggregate or release.</summary>
    public int MaximumDocumentBytes { get; init; } = 16 * 1024 * 1024;
    /// <summary>Maximum bytes accepted for one attachment object.</summary>
    public long MaximumAttachmentObjectBytes { get; init; } = 64 * 1024 * 1024;
    /// <summary>Maximum total quarantined and available attachment bytes.</summary>
    public long MaximumAttachmentBytes { get; init; } = 256 * 1024 * 1024;
}
