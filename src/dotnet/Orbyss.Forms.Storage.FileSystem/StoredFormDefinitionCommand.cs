namespace Orbyss.Forms;

/// <summary>Persists the exact form aggregate originally associated with one idempotency key.</summary>
internal sealed record StoredFormDefinitionCommand(
    string Fingerprint,
    FormDefinition Definition,
    FormCandidate? Candidate,
    IReadOnlyList<string> Evidence,
    FormConcurrencyToken Version,
    int AuditCount);
