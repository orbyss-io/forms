namespace ProgramKit.Forms.Web.Submissions;

/// <summary>Requests one caller-identified resumable draft.</summary>
public sealed record CreateFormDraftRequest(string DraftId, string ReleaseId, string Json, FormWebMutation Mutation);
