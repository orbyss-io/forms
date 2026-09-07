namespace Orbyss.Forms;

/// <summary>Owns governed creation, replacement, retrieval, and semantic validation of form drafts.</summary>
public interface IFormAuthoring
{
    /// <summary>Creates a new form draft.</summary>
    ValueTask<FormMutationResult<FormDefinition>> CreateAsync(
        FormDefinition definition,
        FormMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Gets the current form definition, or returns null when it does not exist.</summary>
    ValueTask<FormDefinition?> GetAsync(FormId formId, CancellationToken cancellationToken = default);

    /// <summary>Replaces the editable definition while enforcing the supplied concurrency token.</summary>
    ValueTask<FormMutationResult<FormDefinition>> ReplaceAsync(
        FormDefinition definition,
        FormMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Validates a definition without mutating stored state.</summary>
    ValueTask<IReadOnlyList<FormDiagnostic>> ValidateAsync(
        FormDefinition definition,
        CancellationToken cancellationToken = default);
}
