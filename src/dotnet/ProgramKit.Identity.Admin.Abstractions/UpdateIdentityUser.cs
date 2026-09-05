namespace ProgramKit.Identity.Admin;
/// <summary>Portable mutable fields used to replace a user account representation.</summary>
public sealed record UpdateIdentityUser(string Username, string? Email, string? FirstName, string? LastName, bool Enabled, bool EmailVerified, IReadOnlyDictionary<string, string[]>? Attributes = null);
