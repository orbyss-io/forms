using System.Text;
using System.Xml;

namespace Orbyss.Localization.Formats;

/// <summary>Exports one scoped target locale as a deterministic XLIFF 2.1 document.</summary>
public sealed class Xliff21LocalizationExportAdapter : ILocalizationExportFormatAdapter
{
    /// <summary>Bounds applied while projecting and encoding XLIFF output.</summary>
    private readonly LocalizationExportFormatOptions options;

    /// <summary>Initializes the XLIFF exporter with secure defaults.</summary>
    public Xliff21LocalizationExportAdapter(LocalizationExportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationExportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Xliff21;

    /// <inheritdoc />
    public ValueTask<LocalizationExportDocument> ExportAsync(LocalizationExportRequest request, CancellationToken cancellationToken = default)
    {
        var entries = ExportGuards.Project(request, Format, options, requireSingleLocale: true, requireScope: true);
        var targetLocale = (request.LanguageTags ?? request.Catalog.Locales.Where(locale => !string.Equals(locale.LanguageTag, request.Catalog.SourceLocale, StringComparison.OrdinalIgnoreCase)).Select(locale => locale.LanguageTag).ToArray()).Single();
        using var output = new MemoryStream();
        using (var writer = XmlWriter.Create(output, new XmlWriterSettings { Encoding = new UTF8Encoding(false), Indent = true, CloseOutput = false }))
        {
            writer.WriteStartDocument();
            writer.WriteStartElement("xliff", "urn:oasis:names:tc:xliff:document:2.0");
            writer.WriteAttributeString("version", "2.1");
            writer.WriteAttributeString("srcLang", request.Catalog.SourceLocale);
            writer.WriteAttributeString("trgLang", targetLocale);
            writer.WriteStartElement("file");
            writer.WriteAttributeString("id", "localization");
            foreach (var entry in entries)
            {
                cancellationToken.ThrowIfCancellationRequested();
                writer.WriteStartElement("unit"); writer.WriteAttributeString("id", entry.Key);
                writer.WriteStartElement("segment");
                writer.WriteElementString("source", entry.SourcePattern);
                writer.WriteElementString("target", entry.Pattern);
                writer.WriteEndElement(); writer.WriteEndElement();
            }
            writer.WriteEndElement(); writer.WriteEndElement(); writer.WriteEndDocument();
        }
        return ValueTask.FromResult(ExportGuards.Document(Format, output.ToArray(), "application/xliff+xml", "xlf", request, options));
    }
}
