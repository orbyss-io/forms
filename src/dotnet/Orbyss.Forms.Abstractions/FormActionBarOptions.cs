namespace Orbyss.Forms;

/// <summary>Declares the ordered, allowlisted actions rendered by one action-bar element.</summary>
public sealed record FormActionBarOptions(IReadOnlyList<string> ActionIds);
