namespace Orbyss.Forms;

/// <summary>Contains current draft/submission state and its exact replay history.</summary>
internal sealed record InMemoryFormResponseDocument(FormSubmissionAggregateSnapshot Snapshot, IReadOnlyList<InMemoryFormResponseReplay> Commands);
