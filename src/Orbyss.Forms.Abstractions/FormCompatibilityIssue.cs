namespace Orbyss.Forms;

/// <summary>Reports one stable compatibility finding between form candidates or releases.</summary>
public sealed record FormCompatibilityIssue(
    string Code,
    FormCompatibilityImpact Impact,
    string Message,
    string? Path = null);
