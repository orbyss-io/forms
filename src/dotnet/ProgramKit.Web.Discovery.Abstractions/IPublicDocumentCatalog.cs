namespace ProgramKit.Web.Discovery;

/// <summary>Supplies an immutable, explicitly public document snapshot for one shell generation.</summary>
public interface IPublicDocumentCatalog
{
    /// <summary>Reads validated public documents; private application content must never be returned.</summary>
    IReadOnlyList<PublicDocument> ReadDocuments();
}
