namespace ProgramKit.Localization;

/// <summary>Bounds localization catalog complexity before import, review, or publication.</summary>
public sealed record LocalizationValidationOptions(
    int MaximumLocales = 100,
    int MaximumMessages = 20_000,
    int MaximumArgumentsPerMessage = 64,
    int MaximumPatternLength = 16_384,
    int MaximumFallbackDepth = 16);
