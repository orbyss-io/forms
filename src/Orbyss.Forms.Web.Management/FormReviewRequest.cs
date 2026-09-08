namespace Orbyss.Forms.Web.Management;

/// <summary>Supplies acceptance-evidence references with one review command.</summary>
public sealed record FormReviewRequest(IReadOnlyList<string> Evidence, FormWebMutation Mutation);
