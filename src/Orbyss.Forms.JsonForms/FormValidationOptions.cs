namespace Orbyss.Forms;

/// <summary>Bounds form complexity before a definition reaches a compiler or renderer.</summary>
public sealed record FormValidationOptions(
    int MaximumFields = 500,
    int MaximumElements = 2_000,
    int MaximumLayoutDepth = 32,
    int MaximumChoicesPerField = 1_000,
    int MaximumPatternLength = 256,
    int MaximumOptionCount = 64);
