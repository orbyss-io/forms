namespace ProgramKit.Localization;

/// <summary>Identifies a structured translation scope without requiring consumers to parse strings.</summary>
public sealed record LocalizationScope(
    LocalizationScopeKind Kind,
    string? ResourceId = null,
    string? ParentResourceId = null);
