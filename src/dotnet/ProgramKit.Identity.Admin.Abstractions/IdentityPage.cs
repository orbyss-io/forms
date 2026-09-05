namespace ProgramKit.Identity.Admin;
/// <summary>A page of identity-provider results and its optional unpaged total.</summary>
public sealed record IdentityPage<T>(IReadOnlyList<T> Items, int? Total = null);
