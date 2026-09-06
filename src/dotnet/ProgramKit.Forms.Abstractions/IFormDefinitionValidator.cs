namespace ProgramKit.Forms;

/// <summary>Validates provider-neutral form definitions without storing or compiling them.</summary>
public interface IFormDefinitionValidator
{
    /// <summary>Returns stable diagnostics for the supplied definition.</summary>
    ValueTask<IReadOnlyList<FormDiagnostic>> ValidateAsync(
        FormDefinition definition,
        CancellationToken cancellationToken = default);
}
