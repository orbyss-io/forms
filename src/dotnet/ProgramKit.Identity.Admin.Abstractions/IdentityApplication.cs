namespace ProgramKit.Identity.Admin;
/// <summary>A provider-neutral application or OAuth client.</summary>
public sealed record IdentityApplication(string Id, string ClientId, string? Name, bool Enabled, bool PublicClient, IReadOnlyList<string> RedirectUris, IReadOnlyList<string> WebOrigins);
