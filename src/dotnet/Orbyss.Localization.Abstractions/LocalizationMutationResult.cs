namespace Orbyss.Localization;

/// <summary>Returns a localization mutation value with its new version and replay status.</summary>
/// <typeparam name="T">The mutation result value.</typeparam>
public sealed record LocalizationMutationResult<T>(
    T Value,
    LocalizationConcurrencyToken Version,
    bool WasReplay);
