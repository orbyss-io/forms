namespace ProgramKit.Forms;

/// <summary>Represents deterministic artifacts and requirements awaiting acceptance and publication.</summary>
public sealed record FormCandidate(
    FormId FormId,
    FormRevision Revision,
    FormArtifact DataSchema,
    FormArtifact UiSchema,
    IReadOnlyList<FormRendererRequirement> Renderers,
    IReadOnlyList<FormTranslationRequirement> Translations,
    IReadOnlyList<FormActionRequirement> Actions,
    IReadOnlyList<FormDiagnostic> Diagnostics,
    DateTimeOffset CompiledAt,
    string CandidateSha256,
    IReadOnlyList<FormFieldDefinition>? Fields = null);
