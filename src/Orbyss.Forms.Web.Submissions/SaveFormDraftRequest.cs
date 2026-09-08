namespace Orbyss.Forms.Web.Submissions;

/// <summary>Requests replacement of one active draft's canonical data.</summary>
public sealed record SaveFormDraftRequest(string Json, FormWebMutation Mutation);
