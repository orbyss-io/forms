namespace ProgramKit.Forms;

/// <summary>Binds separate in-memory retirement state to exact command replay evidence.</summary>
internal sealed record InMemoryFormRetirement(string IdempotencyKey, string Fingerprint, FormConcurrencyToken Version);
