namespace Orbyss.Forms.Management.Tool;

/// <summary>Configures claims used by the default authenticated management-tool actor provider.</summary>
public sealed record FormToolIdentityOptions(string SubjectClaimType = "sub", string ActorKindClaimType = "actor_kind", string DisplayNameClaimType = "name");
