using System.Security.Claims;

namespace Orbyss.Forms.Submissions.Tool;

/// <summary>Builds tool actors exclusively from authenticated transport claims.</summary>
public sealed class ClaimsFormSubmissionToolActorProvider : IFormToolActorProvider
{
    /// <summary>Holds the configured identity claim mappings.</summary>
    private readonly FormSubmissionToolIdentityOptions options;

    /// <summary>Initializes the claims-based provider.</summary>
    public ClaimsFormSubmissionToolActorProvider(FormSubmissionToolIdentityOptions? options = null) => this.options = options ?? new FormSubmissionToolIdentityOptions();

    /// <inheritdoc />
    public ValueTask<FormAuditActor> GetActorAsync(ClaimsPrincipal? principal, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (principal?.Identity?.IsAuthenticated != true) throw new UnauthorizedAccessException("An authenticated tool principal is required.");
        var subject = principal.FindFirst(options.SubjectClaimType)?.Value ?? principal.FindFirst(ClaimTypes.NameIdentifier)?.Value;
        if (string.IsNullOrWhiteSpace(subject)) throw new UnauthorizedAccessException("The authenticated tool principal has no configured subject claim.");
        return ValueTask.FromResult(new FormAuditActor(subject, principal.FindFirst(options.ActorKindClaimType)?.Value ?? "tool-user", principal.FindFirst(options.DisplayNameClaimType)?.Value ?? principal.Identity.Name));
    }
}
