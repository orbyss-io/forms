using System.Text.Json;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>Implements Keycloak-specific authentication-flow administration.</summary>
internal sealed class KeycloakAuthenticationFlowAdministration(KeycloakAdminTransport transport) : IKeycloakAuthenticationFlowAdministration
{
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<JsonElement>> GetFlowsAsync(CancellationToken cancellationToken = default) => KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, "authentication/flows", cancellationToken: cancellationToken), static item => item.Clone());
    /// <inheritdoc />
    public ValueTask<string> CreateFlowAsync(string alias, string? description = null, string providerId = "basic-flow", bool topLevel = true, CancellationToken cancellationToken = default) => transport.CreateAsync("authentication/flows", new { alias, description, providerId, topLevel, builtIn = false }, cancellationToken);
    /// <inheritdoc />
    public ValueTask<string> CopyFlowAsync(string flowAlias, string newName, CancellationToken cancellationToken = default) => transport.CreateAsync($"authentication/flows/{KeycloakAdminTransport.Escape(flowAlias)}/copy", new { newName }, cancellationToken);
    /// <inheritdoc />
    public async ValueTask DeleteFlowAsync(string flowId, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Delete, $"authentication/flows/{KeycloakAdminTransport.Escape(flowId)}", cancellationToken: cancellationToken);
    /// <inheritdoc />
    public async ValueTask<IReadOnlyList<JsonElement>> GetExecutionsAsync(string flowAlias, CancellationToken cancellationToken = default) => KeycloakJson.Array(await transport.SendAsync(HttpMethod.Get, $"authentication/flows/{KeycloakAdminTransport.Escape(flowAlias)}/executions", cancellationToken: cancellationToken), static item => item.Clone());
    /// <inheritdoc />
    public ValueTask<string> AddExecutionAsync(string flowAlias, string provider, CancellationToken cancellationToken = default) => transport.CreateAsync($"authentication/flows/{KeycloakAdminTransport.Escape(flowAlias)}/executions/execution", new { provider }, cancellationToken);
    /// <inheritdoc />
    public async ValueTask UpdateExecutionAsync(string flowAlias, JsonElement execution, CancellationToken cancellationToken = default) => _ = await transport.SendAsync(HttpMethod.Put, $"authentication/flows/{KeycloakAdminTransport.Escape(flowAlias)}/executions", execution, cancellationToken);
}
