namespace Orbyss.Forms;

/// <summary>Pairs a form draft with its opaque optimistic-concurrency version.</summary>
public sealed record FormDraftDocument(FormDraft Draft, FormConcurrencyToken Version);
