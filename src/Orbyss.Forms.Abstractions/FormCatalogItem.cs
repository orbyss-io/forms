namespace Orbyss.Forms;

/// <summary>Provides a bounded form projection for management search results.</summary>
public sealed record FormCatalogItem(
    FormId Id,
    string Name,
    FormRevision Revision,
    FormLifecycleState State,
    FormConcurrencyToken Version);
