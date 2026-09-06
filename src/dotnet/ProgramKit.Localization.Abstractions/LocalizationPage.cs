namespace ProgramKit.Localization;

/// <summary>Returns a bounded page of localization results and an optional total.</summary>
/// <typeparam name="T">The catalog projection type.</typeparam>
public sealed record LocalizationPage<T>(IReadOnlyList<T> Items, int? Total = null);
