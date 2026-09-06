using System.Security.Claims;

namespace ProgramKit.Localization.Tool;

/// <summary>Derives a trusted localization actor from transport-owned identity.</summary>
public interface ILocalizationToolActorProvider
{
    /// <summary>Gets the current actor or rejects missing authenticated identity.</summary>
    ValueTask<LocalizationAuditActor> GetActorAsync(ClaimsPrincipal? principal, CancellationToken cancellationToken = default);
}
