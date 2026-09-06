namespace ProgramKit.Localization;

/// <summary>Stores one locale-specific message pattern and its review provenance.</summary>
public sealed record LocalizedValue(
    string LanguageTag,
    string Pattern,
    LocalizationValueState State,
    string? Provenance = null,
    DateTimeOffset? UpdatedAt = null,
    LocalizationAuditActor? UpdatedBy = null);
