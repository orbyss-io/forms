namespace ProgramKit.Forms;

/// <summary>Requests one atomic, optimistic, durably idempotent form-definition write.</summary>
public sealed record FormDefinitionPersistenceCommand(
    string Operation,
    string Fingerprint,
    FormDefinition Definition,
    FormCandidate? Candidate,
    IReadOnlyList<string> Evidence,
    FormMutationContext Mutation,
    bool RequireAbsent = false);
