namespace ProgramKit.Forms.Web.Submissions;

/// <summary>Requests a separately authorized submission decision.</summary>
public sealed record FormSubmissionDecisionRequest(bool Accept, string? Reason, FormWebMutation Mutation);
