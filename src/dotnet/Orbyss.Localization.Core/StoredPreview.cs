namespace Orbyss.Localization;

/// <summary>Retains the exact parsed entries associated with a hash-bound import preview.</summary>
internal sealed record StoredPreview(
    LocalizationImportPreview Preview,
    IReadOnlyList<LocalizationImportEntry> Entries);
