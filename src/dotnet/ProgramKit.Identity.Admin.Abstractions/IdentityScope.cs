namespace ProgramKit.Identity.Admin;
/// <summary>A provider-neutral OAuth/OIDC client scope.</summary>
public sealed record IdentityScope(string Id, string Name, string? Description);
