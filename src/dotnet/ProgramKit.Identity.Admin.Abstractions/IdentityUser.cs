namespace ProgramKit.Identity.Admin;
/// <summary>A provider-neutral user account.</summary>
public sealed record IdentityUser(string Id, string Username, string? Email, string? FirstName, string? LastName, bool Enabled, bool EmailVerified, IReadOnlyDictionary<string, string[]> Attributes);
