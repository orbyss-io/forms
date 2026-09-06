namespace ProgramKit.Forms;

/// <summary>Analyzes a candidate against an existing immutable form release.</summary>
public interface IFormCompatibilityAnalyzer
{
    /// <summary>Produces stable compatibility findings without mutating either input.</summary>
    ValueTask<FormCompatibilityReport> AnalyzeAsync(
        FormRelease baseline,
        FormCandidate candidate,
        CancellationToken cancellationToken = default);
}
