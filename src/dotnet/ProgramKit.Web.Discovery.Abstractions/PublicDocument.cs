namespace ProgramKit.Web.Discovery;

/// <summary>Represents content deliberately approved for anonymous publication at an exact route.</summary>
/// <param name="Route">The root-relative, literal route without query, wildcards or parameters.</param>
/// <param name="ContentType">The explicit response media type.</param>
/// <param name="Content">The immutable snapshot of the response body.</param>
/// <param name="Index">Whether the document may be indexed; this is not authorization.</param>
public sealed record PublicDocument(string Route, string ContentType, ReadOnlyMemory<byte> Content, bool Index);
