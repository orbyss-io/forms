namespace Orbyss.Localization.Tool;

/// <summary>Maps authenticated claims into provider-neutral localization audit actors.</summary>
public sealed record LocalizationToolIdentityOptions(string SubjectClaimType = "sub", string ActorKindClaimType = "actor_kind", string DisplayNameClaimType = "name");
