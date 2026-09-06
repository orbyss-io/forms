using System.IO.Compression;
using System.Text;
using System.Xml;

namespace ProgramKit.Localization.Formats;

/// <summary>Exports structured wide localization rows as a deterministic formula-free XLSX workbook.</summary>
public sealed class XlsxLocalizationExportAdapter : ILocalizationExportFormatAdapter
{
    /// <summary>Bounds applied while projecting and encoding workbook output.</summary>
    private readonly LocalizationExportFormatOptions options;
    /// <summary>Stable ZIP timestamp used to keep generated workbook bytes reproducible.</summary>
    private static readonly DateTimeOffset ArchiveTimestamp = new(1980, 1, 1, 0, 0, 0, TimeSpan.Zero);

    /// <summary>Initializes the XLSX exporter with secure defaults.</summary>
    public XlsxLocalizationExportAdapter(LocalizationExportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationExportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Xlsx;

    /// <inheritdoc />
    public ValueTask<LocalizationExportDocument> ExportAsync(LocalizationExportRequest request, CancellationToken cancellationToken = default)
    {
        var entries = ExportGuards.Project(request, Format, options);
        var rows = TabularLocalizationExport.CreateRows(request, entries, options);
        using var output = new MemoryStream();
        using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
        {
            WriteContentTypes(archive);
            WriteRootRelationships(archive);
            WriteWorkbook(archive);
            WriteWorkbookRelationships(archive);
            WriteWorksheet(archive, rows, cancellationToken);
        }
        return ValueTask.FromResult(ExportGuards.Document(Format, output.ToArray(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx", request, options));
    }

    /// <summary>Writes the package content-type declarations.</summary>
    private static void WriteContentTypes(ZipArchive archive) => WriteXml(archive, "[Content_Types].xml", writer =>
    {
        writer.WriteStartElement("Types", "http://schemas.openxmlformats.org/package/2006/content-types");
        WriteType(writer, "Default", "Extension", "rels", "application/vnd.openxmlformats-package.relationships+xml");
        WriteType(writer, "Default", "Extension", "xml", "application/xml");
        WriteType(writer, "Override", "PartName", "/xl/workbook.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml");
        WriteType(writer, "Override", "PartName", "/xl/worksheets/sheet1.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml");
        writer.WriteEndElement();
    });

    /// <summary>Writes the package-to-workbook relationship.</summary>
    private static void WriteRootRelationships(ZipArchive archive) => WriteXml(archive, "_rels/.rels", writer =>
    {
        writer.WriteStartElement("Relationships", "http://schemas.openxmlformats.org/package/2006/relationships");
        WriteRelationship(writer, "rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", "xl/workbook.xml");
        writer.WriteEndElement();
    });

    /// <summary>Writes the workbook and its single localization worksheet declaration.</summary>
    private static void WriteWorkbook(ZipArchive archive) => WriteXml(archive, "xl/workbook.xml", writer =>
    {
        writer.WriteStartElement("workbook", "http://schemas.openxmlformats.org/spreadsheetml/2006/main");
        writer.WriteAttributeString("xmlns", "r", null, "http://schemas.openxmlformats.org/officeDocument/2006/relationships");
        writer.WriteStartElement("sheets"); writer.WriteStartElement("sheet");
        writer.WriteAttributeString("name", "Localization"); writer.WriteAttributeString("sheetId", "1");
        writer.WriteAttributeString("r", "id", "http://schemas.openxmlformats.org/officeDocument/2006/relationships", "rId1");
        writer.WriteEndElement(); writer.WriteEndElement(); writer.WriteEndElement();
    });

    /// <summary>Writes the workbook-to-worksheet relationship.</summary>
    private static void WriteWorkbookRelationships(ZipArchive archive) => WriteXml(archive, "xl/_rels/workbook.xml.rels", writer =>
    {
        writer.WriteStartElement("Relationships", "http://schemas.openxmlformats.org/package/2006/relationships");
        WriteRelationship(writer, "rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet", "worksheets/sheet1.xml");
        writer.WriteEndElement();
    });

    /// <summary>Writes every value as an inline string and never creates formula cells.</summary>
    private static void WriteWorksheet(ZipArchive archive, IReadOnlyList<IReadOnlyList<string>> rows, CancellationToken cancellationToken) => WriteXml(archive, "xl/worksheets/sheet1.xml", writer =>
    {
        writer.WriteStartElement("worksheet", "http://schemas.openxmlformats.org/spreadsheetml/2006/main");
        writer.WriteStartElement("sheetData");
        for (var rowIndex = 0; rowIndex < rows.Count; rowIndex++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            writer.WriteStartElement("row"); writer.WriteAttributeString("r", (rowIndex + 1).ToString(System.Globalization.CultureInfo.InvariantCulture));
            for (var columnIndex = 0; columnIndex < rows[rowIndex].Count; columnIndex++)
            {
                writer.WriteStartElement("c"); writer.WriteAttributeString("r", $"{ColumnName(columnIndex)}{rowIndex + 1}"); writer.WriteAttributeString("t", "inlineStr");
                writer.WriteStartElement("is"); writer.WriteStartElement("t"); writer.WriteAttributeString("xml", "space", null, "preserve"); writer.WriteString(rows[rowIndex][columnIndex]);
                writer.WriteEndElement(); writer.WriteEndElement(); writer.WriteEndElement();
            }
            writer.WriteEndElement();
        }
        writer.WriteEndElement(); writer.WriteEndElement();
    });

    /// <summary>Creates one deterministic ZIP entry and writes an XML document into it.</summary>
    private static void WriteXml(ZipArchive archive, string path, Action<XmlWriter> write)
    {
        var entry = archive.CreateEntry(path, CompressionLevel.NoCompression);
        entry.LastWriteTime = ArchiveTimestamp;
        using var stream = entry.Open();
        using var writer = XmlWriter.Create(stream, new XmlWriterSettings { Encoding = new UTF8Encoding(false), Indent = false, CloseOutput = false });
        writer.WriteStartDocument(); write(writer); writer.WriteEndDocument();
    }

    /// <summary>Writes one Open Packaging Convention relationship.</summary>
    private static void WriteRelationship(XmlWriter writer, string id, string type, string target)
    {
        writer.WriteStartElement("Relationship"); writer.WriteAttributeString("Id", id); writer.WriteAttributeString("Type", type); writer.WriteAttributeString("Target", target); writer.WriteEndElement();
    }

    /// <summary>Writes one content-type declaration.</summary>
    private static void WriteType(XmlWriter writer, string element, string identityName, string identityValue, string contentType)
    {
        writer.WriteStartElement(element); writer.WriteAttributeString(identityName, identityValue); writer.WriteAttributeString("ContentType", contentType); writer.WriteEndElement();
    }

    /// <summary>Converts a zero-based column number to its spreadsheet column name.</summary>
    private static string ColumnName(int index)
    {
        var result = string.Empty;
        for (var value = index + 1; value > 0; value = (value - 1) / 26) result = (char)('A' + (value - 1) % 26) + result;
        return result;
    }
}
