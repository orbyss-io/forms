using System.Security.Claims;

namespace Orbyss.Forms.Tool;

/// <summary>Derives a trusted operational actor from transport-owned identity.</summary>
public interface IFormToolActorProvider
{
    /// <summary>Gets an actor for the current tool call or rejects missing identity.</summary>
    ValueTask<FormAuditActor> GetActorAsync(ClaimsPrincipal? principal, CancellationToken cancellationToken = default);
}
