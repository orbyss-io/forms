namespace Orbyss.Forms;

/// <summary>Contains canonical UTF-8 JSON form data and its lowercase SHA-256 digest.</summary>
public sealed record FormDataDocument(string Json, string Sha256);
