using System.Text.Json;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Keycloak-specific authentication-flow administration.</summary>
public interface IKeycloakAuthenticationFlowAdministration
{
    /// <summary>Gets every authentication flow in the configured realm.</summary>
    ValueTask<IReadOnlyList<JsonElement>> GetFlowsAsync(CancellationToken cancellationToken = default);
    /// <summary>Creates a top-level or nested authentication flow and returns its identifier.</summary>
    ValueTask<string> CreateFlowAsync(string alias, string? description = null, string providerId = "basic-flow", bool topLevel = true, CancellationToken cancellationToken = default);
    /// <summary>Copies an authentication flow under a new name and returns its identifier.</summary>
    ValueTask<string> CopyFlowAsync(string flowAlias, string newName, CancellationToken cancellationToken = default);
    /// <summary>Deletes an authentication flow by identifier.</summary>
    ValueTask DeleteFlowAsync(string flowId, CancellationToken cancellationToken = default);
    /// <summary>Gets the execution tree for an authentication-flow alias.</summary>
    ValueTask<IReadOnlyList<JsonElement>> GetExecutionsAsync(string flowAlias, CancellationToken cancellationToken = default);
    /// <summary>Adds an authenticator execution to a flow and returns its identifier.</summary>
    ValueTask<string> AddExecutionAsync(string flowAlias, string provider, CancellationToken cancellationToken = default);
    /// <summary>Updates the requirement and settings represented by a flow execution.</summary>
    ValueTask UpdateExecutionAsync(string flowAlias, JsonElement execution, CancellationToken cancellationToken = default);
}
