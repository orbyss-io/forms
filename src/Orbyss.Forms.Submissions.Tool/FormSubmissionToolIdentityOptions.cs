namespace Orbyss.Forms.Submissions.Tool;

/// <summary>Configures claims used by the default authenticated tool actor provider.</summary>
public sealed record FormSubmissionToolIdentityOptions(string SubjectClaimType = "sub", string ActorKindClaimType = "actor_kind", string DisplayNameClaimType = "name");
