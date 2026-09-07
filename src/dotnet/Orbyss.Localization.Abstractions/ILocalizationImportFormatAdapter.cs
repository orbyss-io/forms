namespace Orbyss.Localization;

/// <summary>Parses one bounded localization interchange format into provider-neutral entries.</summary>
public interface ILocalizationImportFormatAdapter
{
    /// <summary>Gets the format handled by this adapter.</summary>
    LocalizationImportFormat Format { get; }

    /// <summary>Parses untrusted import bytes without mutating catalog state.</summary>
    ValueTask<LocalizationImportDocument> ParseAsync(
        LocalizationImportRequest request,
        CancellationToken cancellationToken = default);
}
