namespace ProgramKit.Localization;

/// <summary>Reports the exact message and fallback selected for a runtime request.</summary>
public sealed record LocalizationResolution(
    string Key,
    LocalizationScope Scope,
    string RequestedLanguageTag,
    string ResolvedLanguageTag,
    TextDirection Direction,
    string Pattern,
    bool UsedFallback);
