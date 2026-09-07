using System.Text;

namespace Orbyss.Localization.Formats;

/// <summary>Exports deterministic UTF-8 CSV with explicit structured scopes and wide locale columns.</summary>
public sealed class CsvLocalizationExportAdapter : ILocalizationExportFormatAdapter
{
    /// <summary>Bounds applied while projecting and encoding CSV output.</summary>
    private readonly LocalizationExportFormatOptions options;

    /// <summary>Initializes the CSV exporter with secure defaults.</summary>
    public CsvLocalizationExportAdapter(LocalizationExportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationExportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Csv;

    /// <inheritdoc />
    public ValueTask<LocalizationExportDocument> ExportAsync(LocalizationExportRequest request, CancellationToken cancellationToken = default)
    {
        var entries = ExportGuards.Project(request, Format, options);
        var rows = TabularLocalizationExport.CreateRows(request, entries, options);
        var output = new StringBuilder();
        foreach (var row in rows)
        {
            cancellationToken.ThrowIfCancellationRequested();
            output.AppendJoin(',', row.Select(Escape));
            output.Append("\r\n");
        }
        return ValueTask.FromResult(ExportGuards.Document(Format, new UTF8Encoding(false).GetBytes(output.ToString()), "text/csv; charset=utf-8", "csv", request, options));
    }

    /// <summary>Escapes one field according to RFC 4180 without changing its data.</summary>
    private static string Escape(string value) => value.IndexOfAny([',', '"', '\r', '\n']) >= 0 ? $"\"{value.Replace("\"", "\"\"", StringComparison.Ordinal)}\"" : value;
}
