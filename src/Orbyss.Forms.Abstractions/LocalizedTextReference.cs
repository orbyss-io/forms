namespace Orbyss.Forms;

/// <summary>References translated text while preserving a source-language fallback.</summary>
public sealed record LocalizedTextReference(string Key, string DefaultText, string? Context = null);
