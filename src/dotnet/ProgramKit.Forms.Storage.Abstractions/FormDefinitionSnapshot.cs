namespace ProgramKit.Forms;

/// <summary>Returns the current definition, prepared candidate, evidence, version, and audit history.</summary>
public sealed record FormDefinitionSnapshot(
    FormDefinition Definition,
    FormCandidate? Candidate,
    IReadOnlyList<string> Evidence,
    FormConcurrencyToken Version,
    IReadOnlyList<FormDefinitionAuditEntry> AuditTrail);
