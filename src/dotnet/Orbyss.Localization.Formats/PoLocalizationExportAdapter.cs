using System.Text;
using System.Text.Json;

namespace Orbyss.Localization.Formats;

/// <summary>Exports one scoped target locale as deterministic singular GNU gettext PO entries.</summary>
public sealed class PoLocalizationExportAdapter : ILocalizationExportFormatAdapter
{
    /// <summary>Bounds applied while projecting and encoding gettext output.</summary>
    private readonly LocalizationExportFormatOptions options;

    /// <summary>Initializes the PO exporter with secure defaults.</summary>
    public PoLocalizationExportAdapter(LocalizationExportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationExportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Po;

    /// <inheritdoc />
    public ValueTask<LocalizationExportDocument> ExportAsync(LocalizationExportRequest request, CancellationToken cancellationToken = default)
    {
        var entries = ExportGuards.Project(request, Format, options, requireSingleLocale: true, requireScope: true);
        var output = new StringBuilder();
        foreach (var entry in entries)
        {
            cancellationToken.ThrowIfCancellationRequested();
            output.Append("msgctxt ").Append(Quote(entry.Key)).Append('\n');
            output.Append("msgid ").Append(Quote(entry.SourcePattern)).Append('\n');
            output.Append("msgstr ").Append(Quote(entry.Pattern)).Append("\n\n");
        }
        return ValueTask.FromResult(ExportGuards.Document(Format, new UTF8Encoding(false).GetBytes(output.ToString()), "text/x-gettext-translation; charset=utf-8", "po", request, options));
    }

    /// <summary>Encodes a PO string with deterministic JSON-compatible escaping.</summary>
    private static string Quote(string value) => JsonSerializer.Serialize(value);
}
