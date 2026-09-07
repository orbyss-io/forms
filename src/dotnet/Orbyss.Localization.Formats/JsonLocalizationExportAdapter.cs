using System.Text.Json;

namespace Orbyss.Localization.Formats;

/// <summary>Exports deterministic structured Orbyss Forms JSON localization documents.</summary>
public sealed class JsonLocalizationExportAdapter : ILocalizationExportFormatAdapter
{
    /// <summary>Bounds applied while projecting and encoding JSON output.</summary>
    private readonly LocalizationExportFormatOptions options;
    /// <summary>Stable camel-case JSON settings without polymorphic or executable metadata.</summary>
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web) { WriteIndented = true };

    /// <summary>Initializes the JSON exporter with secure defaults.</summary>
    public JsonLocalizationExportAdapter(LocalizationExportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationExportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Json;

    /// <inheritdoc />
    public ValueTask<LocalizationExportDocument> ExportAsync(LocalizationExportRequest request, CancellationToken cancellationToken = default)
    {
        var entries = ExportGuards.Project(request, Format, options);
        cancellationToken.ThrowIfCancellationRequested();
        var model = new
        {
            entries = entries.Select(entry => new
            {
                entry.Key,
                entry.LanguageTag,
                entry.Pattern,
                entry.SourcePattern,
                scope = new { kind = entry.Scope.Kind.ToString(), entry.Scope.ResourceId, entry.Scope.ParentResourceId },
                arguments = entry.Arguments.Select(argument => new { argument.Name, type = argument.Type.ToString(), argument.Required }),
                entry.Description,
                entry.Context,
                entry.Provenance
            })
        };
        var content = JsonSerializer.SerializeToUtf8Bytes(model, JsonOptions);
        return ValueTask.FromResult(ExportGuards.Document(Format, content, "application/json", "json", request, options));
    }
}
