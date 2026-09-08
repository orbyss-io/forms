namespace Orbyss.Forms.Web.Submissions;

/// <summary>Requests authoritative submission with explicitly selected clean attachments.</summary>
public sealed record SubmitFormDraftRequest(IReadOnlyList<string> AttachmentIds, FormWebMutation Mutation);
