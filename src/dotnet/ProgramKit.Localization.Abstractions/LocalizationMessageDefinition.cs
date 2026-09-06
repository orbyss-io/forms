namespace ProgramKit.Localization;

/// <summary>Defines one stable message key, source pattern, arguments, and translated values.</summary>
public sealed record LocalizationMessageDefinition(
    string Key,
    LocalizationScope Scope,
    string SourcePattern,
    IReadOnlyList<LocalizationArgumentDefinition> Arguments,
    IReadOnlyList<LocalizedValue> Values,
    string? Description = null,
    string? Context = null);
