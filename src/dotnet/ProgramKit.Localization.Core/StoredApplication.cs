namespace ProgramKit.Localization;

/// <summary>Retains a completed import application for safe idempotent replay.</summary>
internal sealed record StoredApplication(
    string Fingerprint,
    LocalizationMutationResult<LocalizationImportApplicationResult> Result);
