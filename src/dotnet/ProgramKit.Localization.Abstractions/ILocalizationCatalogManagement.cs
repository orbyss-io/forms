namespace ProgramKit.Localization;

/// <summary>Owns governed localization catalog authoring and hash-bound import application.</summary>
public interface ILocalizationCatalogManagement
{
    /// <summary>Creates a new localization catalog draft.</summary>
    ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> CreateAsync(
        LocalizationCatalogDefinition catalog,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Gets the current catalog definition, or returns null when it does not exist.</summary>
    ValueTask<LocalizationCatalogDefinition?> GetAsync(
        LocalizationCatalogId catalogId,
        CancellationToken cancellationToken = default);

    /// <summary>Replaces an editable catalog while enforcing the supplied concurrency token.</summary>
    ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> ReplaceAsync(
        LocalizationCatalogDefinition catalog,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Parses and validates untrusted content without mutating the catalog.</summary>
    ValueTask<LocalizationImportPreview> PreviewImportAsync(
        LocalizationCatalogId catalogId,
        LocalizationImportRequest request,
        CancellationToken cancellationToken = default);

    /// <summary>Applies the exact stored import preview after concurrency and authorization checks.</summary>
    ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> ApplyImportAsync(
        LocalizationCatalogId catalogId,
        string previewId,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default);

    /// <summary>Validates a catalog without mutating stored state.</summary>
    ValueTask<IReadOnlyList<LocalizationDiagnostic>> ValidateAsync(
        LocalizationCatalogDefinition catalog,
        CancellationToken cancellationToken = default);
}
