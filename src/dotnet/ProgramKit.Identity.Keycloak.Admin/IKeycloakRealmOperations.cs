using System.Text.Json;
namespace ProgramKit.Identity.Keycloak.Admin;
/// <summary>High-privilege Keycloak realm operations kept outside portable identity contracts.</summary>
public interface IKeycloakRealmOperations
{
    /// <summary>Gets active and passive signing-key metadata without exporting private keys.</summary>
    ValueTask<JsonElement> GetKeyMetadataAsync(CancellationToken cancellationToken = default);
    /// <summary>Gets realm event recording and listener configuration.</summary>
    ValueTask<JsonElement> GetEventConfigurationAsync(CancellationToken cancellationToken = default);
    /// <summary>Updates realm event recording and listener configuration.</summary>
    ValueTask UpdateEventConfigurationAsync(JsonElement configuration, CancellationToken cancellationToken = default);
    /// <summary>Gets a bounded page of recorded realm events.</summary>
    ValueTask<IReadOnlyList<JsonElement>> GetEventsAsync(int first = 0, int maximum = 100, CancellationToken cancellationToken = default);
    /// <summary>Deletes every recorded realm event.</summary>
    ValueTask DeleteEventsAsync(CancellationToken cancellationToken = default);
    /// <summary>Clears brute-force login failures for one user.</summary>
    ValueTask ClearUserLoginFailuresAsync(string userId, CancellationToken cancellationToken = default);
    /// <summary>Clears brute-force login failures for every user in the realm.</summary>
    ValueTask ClearAllLoginFailuresAsync(CancellationToken cancellationToken = default);
}
