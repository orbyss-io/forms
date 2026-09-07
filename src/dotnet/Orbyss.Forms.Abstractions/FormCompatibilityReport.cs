namespace Orbyss.Forms;

/// <summary>Summarizes compatibility between a baseline release and a candidate.</summary>
public sealed record FormCompatibilityReport(
    FormReleaseId BaselineReleaseId,
    FormRevision CandidateRevision,
    IReadOnlyList<FormCompatibilityIssue> Issues)
{
    /// <summary>Gets whether an explicit migration is required.</summary>
    public bool RequiresMigration => Issues.Any(issue => issue.Impact == FormCompatibilityImpact.Breaking);
}
