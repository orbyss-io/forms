namespace ProgramKit.Identity.Admin;
/// <summary>A provider-neutral login session.</summary>
public sealed record IdentitySession(string Id, string UserId, string? IpAddress, long? StartedAtUnixMilliseconds, long? LastAccessAtUnixMilliseconds, IReadOnlyList<string> ClientIds);
