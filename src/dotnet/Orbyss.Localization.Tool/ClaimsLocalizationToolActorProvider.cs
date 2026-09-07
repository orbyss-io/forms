using System.Security.Claims;

namespace Orbyss.Localization.Tool;

/// <summary>Builds localization audit actors exclusively from authenticated transport claims.</summary>
public sealed class ClaimsLocalizationToolActorProvider : ILocalizationToolActorProvider
{
    /// <summary>Holds configured identity claim mappings.</summary>
    private readonly LocalizationToolIdentityOptions options;

    /// <summary>Initializes a claims-based actor provider.</summary>
    public ClaimsLocalizationToolActorProvider(LocalizationToolIdentityOptions? options = null) => this.options = options ?? new LocalizationToolIdentityOptions();

    /// <inheritdoc />
    public ValueTask<LocalizationAuditActor> GetActorAsync(ClaimsPrincipal? principal, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (principal?.Identity?.IsAuthenticated != true) throw new UnauthorizedAccessException("An authenticated localization tool principal is required.");
        var subject = principal.FindFirst(options.SubjectClaimType)?.Value ?? principal.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrWhiteSpace(subject)) throw new UnauthorizedAccessException("The authenticated localization tool principal has no configured subject claim.");
        return ValueTask.FromResult(new LocalizationAuditActor(subject, principal.FindFirst(options.ActorKindClaimType)?.Value ?? "tool-user", principal.FindFirst(options.DisplayNameClaimType)?.Value ?? principal.Identity.Name));
    }
}
