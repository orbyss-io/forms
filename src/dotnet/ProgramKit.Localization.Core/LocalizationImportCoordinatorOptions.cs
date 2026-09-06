namespace ProgramKit.Localization;

/// <summary>Bounds short-lived hash-bound import previews retained by one coordinator instance.</summary>
public sealed record LocalizationImportCoordinatorOptions(int MaximumStoredPreviews = 1_000);
