using System.Security.Claims;

namespace Orbyss.Forms.Management.Tool;

/// <summary>Derives a trusted management actor from transport-owned identity.</summary>
public interface IFormToolActorProvider
{
    /// <summary>Gets an actor for the current tool call or rejects missing identity.</summary>
    ValueTask<FormAuditActor> GetActorAsync(ClaimsPrincipal? principal, CancellationToken cancellationToken = default);
}
