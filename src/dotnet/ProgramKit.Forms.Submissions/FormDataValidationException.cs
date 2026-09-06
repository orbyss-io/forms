namespace ProgramKit.Forms;

/// <summary>Reports public-safe authoritative form data diagnostics.</summary>
public sealed class FormDataValidationException : InvalidOperationException
{
    /// <summary>Initializes a failed validation with its bounded diagnostics.</summary>
    public FormDataValidationException(IReadOnlyList<FormDataDiagnostic> diagnostics)
        : base("Form data failed authoritative validation.") => Diagnostics = diagnostics ?? throw new ArgumentNullException(nameof(diagnostics));

    /// <summary>Gets the authoritative diagnostics.</summary>
    public IReadOnlyList<FormDataDiagnostic> Diagnostics { get; }
}
