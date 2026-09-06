namespace ProgramKit.Forms;

/// <summary>Configures bounded filesystem persistence for editable form aggregates.</summary>
public sealed record FileSystemFormDefinitionStoreOptions(
    string DirectoryPath,
    int MaximumDocumentBytes = 16 * 1024 * 1024,
    int MaximumForms = 100_000);
