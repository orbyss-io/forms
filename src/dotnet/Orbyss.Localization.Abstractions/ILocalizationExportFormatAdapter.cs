namespace Orbyss.Localization;

/// <summary>Serializes a governed localization catalog into one bounded interchange format.</summary>
public interface ILocalizationExportFormatAdapter
{
    /// <summary>Gets the format handled by this adapter.</summary>
    LocalizationImportFormat Format { get; }

    /// <summary>Exports selected catalog content without changing catalog state.</summary>
    ValueTask<LocalizationExportDocument> ExportAsync(
        LocalizationExportRequest request,
        CancellationToken cancellationToken = default);
}
