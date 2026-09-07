namespace Orbyss.Localization;

/// <summary>Validates localization catalogs without persisting or publishing them.</summary>
public interface ILocalizationCatalogValidator
{
    /// <summary>Returns stable diagnostics for the supplied editable catalog.</summary>
    ValueTask<IReadOnlyList<LocalizationDiagnostic>> ValidateAsync(
        LocalizationCatalogDefinition catalog,
        CancellationToken cancellationToken = default);
}
