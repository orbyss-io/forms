namespace Orbyss.Forms;

/// <summary>Requests an allowlisted renderer component and a compatible version range.</summary>
public sealed record FormComponentReference(
    string ComponentId,
    string VersionRange,
    IReadOnlyDictionary<string, string>? Options = null);
