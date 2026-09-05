namespace ProgramKit.Identity.Admin;
/// <summary>Portable fields used to create a user account.</summary>
public sealed record CreateIdentityUser(string Username, string? Email = null, string? FirstName = null, string? LastName = null, bool Enabled = true, bool EmailVerified = false, IReadOnlyDictionary<string, string[]>? Attributes = null);
