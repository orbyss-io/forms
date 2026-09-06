namespace ProgramKit.Forms;

/// <summary>Persists mutable retirement state separately from immutable form release content.</summary>
public interface IFormReleaseRetirementStore
{
    /// <summary>Retires one release through an optimistic and durably idempotent mutation.</summary>
    ValueTask<FormMutationResult<FormRelease>> RetireAsync(
        FormReleaseId releaseId,
        string fingerprint,
        FormMutationContext mutation,
        CancellationToken cancellationToken = default);
}
