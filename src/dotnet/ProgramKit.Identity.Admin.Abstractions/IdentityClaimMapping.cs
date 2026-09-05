namespace ProgramKit.Identity.Admin;
/// <summary>A portable token claim mapping backed by a user attribute.</summary>
public sealed record IdentityClaimMapping(string Name, string UserAttribute, string TokenClaim, string ClaimType = "String", bool IncludeInAccessToken = true, bool IncludeInIdToken = true, bool IncludeInUserInfo = true);
