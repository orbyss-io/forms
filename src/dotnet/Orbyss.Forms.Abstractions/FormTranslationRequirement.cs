namespace Orbyss.Forms;

/// <summary>Declares one localized message required by a compiled form release.</summary>
public sealed record FormTranslationRequirement(
    string Key,
    string DefaultText,
    string SourceLocale,
    string Scope,
    string? Context = null,
    IReadOnlyList<string>? Arguments = null);
