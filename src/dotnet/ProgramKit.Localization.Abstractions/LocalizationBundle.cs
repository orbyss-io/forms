namespace ProgramKit.Localization;

/// <summary>Provides a bounded immutable set of runtime messages for one locale and scope.</summary>
public sealed record LocalizationBundle(
    LocalizationReleaseId ReleaseId,
    LocalizationScope Scope,
    string RequestedLanguageTag,
    string ResolvedLanguageTag,
    TextDirection Direction,
    IReadOnlyDictionary<string, string> Messages,
    string Sha256);
