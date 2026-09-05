namespace ProgramKit.Identity.Admin;
/// <summary>A provider-neutral group.</summary>
public sealed record IdentityGroup(string Id, string Name, string? Path = null);
