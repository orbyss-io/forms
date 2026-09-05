namespace ProgramKit.Identity.Admin;
/// <summary>A provider-neutral enrolled credential.</summary>
public sealed record IdentityCredential(string Id, string Type, string? DisplayName, long? CreatedAtUnixMilliseconds);
