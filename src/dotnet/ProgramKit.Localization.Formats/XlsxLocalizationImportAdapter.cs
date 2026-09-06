using System.Globalization;
using System.IO.Compression;
using System.Xml.Linq;

namespace ProgramKit.Localization.Formats;

/// <summary>Reads cell text from one bounded XLSX worksheet without evaluating formulas or active content.</summary>
public sealed class XlsxLocalizationImportAdapter : ILocalizationImportFormatAdapter
{
    /// <summary>Bounds applied while expanding and decoding workbook input.</summary>
    private readonly LocalizationImportFormatOptions options;

    /// <summary>Initializes the XLSX adapter with secure defaults.</summary>
    public XlsxLocalizationImportAdapter(LocalizationImportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationImportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Xlsx;

    /// <inheritdoc />
    public ValueTask<LocalizationImportDocument> ParseAsync(LocalizationImportRequest request, CancellationToken cancellationToken = default)
    {
        FormatGuards.RequireFormatAndBounds(request, Format, options);
        using var stream = new MemoryStream(request.Content.ToArray(), writable: false);
        using ZipArchive archive = OpenArchive(stream);
        if (archive.Entries.Count > options.MaximumArchiveEntries) throw new LocalizationImportFormatException("PKLI501", "XLSX archive expansion limits were exceeded.");
        long expandedBytes = 0;
        foreach (var archiveEntry in archive.Entries)
        {
            if (archiveEntry.Length > options.MaximumExpandedBytes - expandedBytes) throw new LocalizationImportFormatException("PKLI501", "XLSX archive expansion limits were exceeded.");
            expandedBytes += archiveEntry.Length;
        }
        if (archive.Entries.Any(entry => entry.FullName.EndsWith("vbaProject.bin", StringComparison.OrdinalIgnoreCase))) throw new LocalizationImportFormatException("PKLI502", "Macro-enabled workbook content is not accepted.");
        var shared = ReadSharedStrings(archive, cancellationToken);
        var sheetName = request.Mapping?.GetValueOrDefault("sheet") ?? "sheet1";
        if (!System.Text.RegularExpressions.Regex.IsMatch(sheetName, "^sheet[1-9][0-9]*$", System.Text.RegularExpressions.RegexOptions.IgnoreCase | System.Text.RegularExpressions.RegexOptions.CultureInvariant)) throw new LocalizationImportFormatException("PKLI503", "XLSX sheet mapping must use a bounded worksheet identity such as sheet1.");
        var entry = archive.GetEntry($"xl/worksheets/{sheetName.ToLowerInvariant()}.xml") ?? throw new LocalizationImportFormatException("PKLI504", "The mapped XLSX worksheet was not found.");
        var document = ReadEntryXml(entry);
        var rows = new List<IReadOnlyList<string>>();
        foreach (var row in document.Descendants().Where(element => element.Name.LocalName == "row"))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (rows.Count >= options.MaximumRows + 1) throw new LocalizationImportFormatException("PKLI505", "XLSX row limit exceeded.");
            var cells = new SortedDictionary<int, string>();
            foreach (var cell in row.Elements().Where(element => element.Name.LocalName == "c"))
            {
                if (cell.Elements().Any(element => element.Name.LocalName == "f")) throw new LocalizationImportFormatException("PKLI506", "XLSX formulas are not accepted as localization input.");
                var column = ColumnIndex(cell.Attribute("r")?.Value);
                if (column >= options.MaximumColumns) throw new LocalizationImportFormatException("PKLI507", "XLSX column limit exceeded.");
                var type = cell.Attribute("t")?.Value;
                var raw = cell.Elements().FirstOrDefault(element => element.Name.LocalName == "v")?.Value
                    ?? cell.Descendants().FirstOrDefault(element => element.Name.LocalName == "t")?.Value
                    ?? string.Empty;
                var value = type == "s" && int.TryParse(raw, NumberStyles.None, CultureInfo.InvariantCulture, out var sharedIndex) && sharedIndex >= 0 && sharedIndex < shared.Count ? shared[sharedIndex] : raw;
                if (value.Length > options.MaximumCellCharacters) throw new LocalizationImportFormatException("PKLI508", "XLSX cell exceeds the configured character limit.");
                cells[column] = value;
            }
            var width = cells.Count == 0 ? 0 : cells.Keys.Max() + 1;
            rows.Add(Enumerable.Range(0, width).Select(index => cells.GetValueOrDefault(index) ?? string.Empty).ToArray());
        }
        return ValueTask.FromResult(TabularLocalizationImport.Parse(rows, request, options));
    }

    /// <summary>Opens the workbook container while normalizing invalid archive failures.</summary>
    private static ZipArchive OpenArchive(Stream stream)
    {
        try { return new ZipArchive(stream, ZipArchiveMode.Read, leaveOpen: true); }
        catch (InvalidDataException) { throw new LocalizationImportFormatException("PKLI509", "XLSX content is not a valid ZIP archive."); }
    }

    /// <summary>Reads bounded shared-string values without resolving external workbook content.</summary>
    private List<string> ReadSharedStrings(ZipArchive archive, CancellationToken cancellationToken)
    {
        var entry = archive.GetEntry("xl/sharedStrings.xml");
        if (entry is null) return [];
        var document = ReadEntryXml(entry);
        var values = document.Descendants().Where(element => element.Name.LocalName == "si").Select(item => string.Concat(item.Descendants().Where(element => element.Name.LocalName == "t").Select(text => text.Value))).ToList();
        if (values.Count > options.MaximumRows * options.MaximumColumns || values.Any(value => value.Length > options.MaximumCellCharacters)) throw new LocalizationImportFormatException("PKLI510", "XLSX shared string limits were exceeded.");
        cancellationToken.ThrowIfCancellationRequested();
        return values;
    }

    /// <summary>Copies and securely parses one bounded XML archive part.</summary>
    private XDocument ReadEntryXml(ZipArchiveEntry entry)
    {
        if (entry.Length > options.MaximumExpandedBytes) throw new LocalizationImportFormatException("PKLI511", "XLSX XML part exceeds the configured expansion limit.");
        using var stream = entry.Open();
        using var buffer = new MemoryStream();
        stream.CopyTo(buffer);
        return XmlImport.Read(buffer.ToArray(), options);
    }

    /// <summary>Converts an A1-style cell reference into its zero-based column position.</summary>
    private static int ColumnIndex(string? reference)
    {
        if (string.IsNullOrWhiteSpace(reference)) return 0;
        var result = 0;
        try
        {
            foreach (var character in reference.TakeWhile(char.IsAsciiLetter)) result = checked(result * 26 + char.ToUpperInvariant(character) - 'A' + 1);
        }
        catch (OverflowException)
        {
            throw new LocalizationImportFormatException("PKLI512", "XLSX cell reference exceeds the supported column range.");
        }
        return Math.Max(0, result - 1);
    }
}
