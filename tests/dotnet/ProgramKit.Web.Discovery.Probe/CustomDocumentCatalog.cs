using ProgramKit.Web.Discovery;

/// <summary>Exercises the consumer-owned adapter replacement contract.</summary>
internal sealed class CustomDocumentCatalog : IPublicDocumentCatalog
{
    /// <inheritdoc />
    public IReadOnlyList<PublicDocument> ReadDocuments() => [];
}
