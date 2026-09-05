namespace ProgramKit.Identity.Admin;
/// <summary>Portable fields used to create or replace an OAuth/OIDC application.</summary>
public sealed record CreateIdentityApplication(string ClientId, string? Name = null, bool Enabled = true, bool PublicClient = false, IReadOnlyList<string>? RedirectUris = null, IReadOnlyList<string>? WebOrigins = null, bool ServiceAccountsEnabled = false);
