namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Holds a Keycloak service-account token and its absolute expiry.</summary>
internal sealed record AccessToken(string Value, DateTimeOffset ExpiresAt);
