namespace Orbyss.Forms;

/// <summary>Performs authoritative provider-neutral checks against one immutable form release.</summary>
public interface IFormDataValidator
{
    /// <summary>Validates canonical JSON data for a draft save or final submission.</summary>
    ValueTask<IReadOnlyList<FormDataDiagnostic>> ValidateAsync(
        FormRelease release,
        FormDataDocument data,
        FormDataValidationMode mode,
        CancellationToken cancellationToken = default);
}
