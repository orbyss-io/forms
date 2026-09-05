using System.Text.Json;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Keycloak-specific external identity-provider and mapper administration.</summary>
public interface IKeycloakIdentityProviderAdministration
{
    /// <summary>Gets all external identity-provider representations.</summary>
    ValueTask<IReadOnlyList<JsonElement>> GetAllAsync(CancellationToken cancellationToken = default);
    /// <summary>Gets an external provider by alias, or returns null when absent.</summary>
    ValueTask<JsonElement?> GetAsync(string alias, CancellationToken cancellationToken = default);
    /// <summary>Creates an external identity provider and returns its identifier.</summary>
    ValueTask<string> CreateAsync(JsonElement representation, CancellationToken cancellationToken = default);
    /// <summary>Updates an external identity provider by alias.</summary>
    ValueTask UpdateAsync(string alias, JsonElement representation, CancellationToken cancellationToken = default);
    /// <summary>Deletes an external identity provider by alias.</summary>
    ValueTask DeleteAsync(string alias, CancellationToken cancellationToken = default);
    /// <summary>Gets all mappers configured for an external identity provider.</summary>
    ValueTask<IReadOnlyList<JsonElement>> GetMappersAsync(string alias, CancellationToken cancellationToken = default);
    /// <summary>Creates a mapper for an external identity provider.</summary>
    ValueTask CreateMapperAsync(string alias, JsonElement representation, CancellationToken cancellationToken = default);
    /// <summary>Updates an external identity-provider mapper.</summary>
    ValueTask UpdateMapperAsync(string alias, string mapperId, JsonElement representation, CancellationToken cancellationToken = default);
    /// <summary>Deletes an external identity-provider mapper.</summary>
    ValueTask DeleteMapperAsync(string alias, string mapperId, CancellationToken cancellationToken = default);
}
