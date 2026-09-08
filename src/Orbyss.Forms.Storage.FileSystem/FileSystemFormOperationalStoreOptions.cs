namespace Orbyss.Forms;

/// <summary>Configures bounded filesystem persistence for drafts, submissions, metadata, and content.</summary>
public sealed record FileSystemFormOperationalStoreOptions(
    string DirectoryPath,
    int MaximumDocumentBytes = 16_777_216,
    int MaximumDocuments = 100_000,
    int MaximumCommandsPerDocument = 10_000);
