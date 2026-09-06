namespace ProgramKit.Forms;

/// <summary>Contains one current editable form aggregate and its durable command history.</summary>
internal sealed record StoredFormDefinitionDocument(
    FormDefinition Definition,
    FormCandidate? Candidate,
    IReadOnlyList<string> Evidence,
    FormConcurrencyToken Version,
    IReadOnlyList<FormDefinitionAuditEntry> AuditTrail,
    IReadOnlyDictionary<string, StoredFormDefinitionCommand> Commands);
