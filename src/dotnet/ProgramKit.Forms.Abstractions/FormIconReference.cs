namespace ProgramKit.Forms;

/// <summary>References an icon from an installed, validated icon registry.</summary>
public sealed record FormIconReference(string Name, string? Bundle = null);
