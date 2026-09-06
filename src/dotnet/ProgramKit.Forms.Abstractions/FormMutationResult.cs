namespace ProgramKit.Forms;

/// <summary>Returns a form mutation value with its new version and replay status.</summary>
/// <typeparam name="T">The mutation result value.</typeparam>
public sealed record FormMutationResult<T>(T Value, FormConcurrencyToken Version, bool WasReplay);
