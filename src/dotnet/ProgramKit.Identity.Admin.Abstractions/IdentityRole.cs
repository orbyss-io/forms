namespace ProgramKit.Identity.Admin;
/// <summary>A provider-neutral role.</summary>
public sealed record IdentityRole(string Id, string Name, string? Description, bool Composite = false);
