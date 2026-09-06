using System.Xml;
using System.Xml.Linq;

namespace ProgramKit.Localization.Formats;

/// <summary>Parses bounded XLIFF 2.1 unit segments using explicit source and target text.</summary>
public sealed class Xliff21LocalizationImportAdapter : ILocalizationImportFormatAdapter
{
    /// <summary>Bounds applied while decoding XLIFF input.</summary>
    private readonly LocalizationImportFormatOptions options;

    /// <summary>Initializes the XLIFF adapter with secure defaults.</summary>
    public Xliff21LocalizationImportAdapter(LocalizationImportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationImportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Xliff21;

    /// <inheritdoc />
    public ValueTask<LocalizationImportDocument> ParseAsync(LocalizationImportRequest request, CancellationToken cancellationToken = default)
    {
        FormatGuards.RequireFormatAndBounds(request, Format, options);
        var document = XmlImport.Read(request.Content, options);
        var root = document.Root ?? throw new LocalizationImportFormatException("PKLI401", "XLIFF content has no document element.");
        if (!string.Equals(root.Name.LocalName, "xliff", StringComparison.Ordinal) || root.Attribute("version")?.Value != "2.1") throw new LocalizationImportFormatException("PKLI402", "XLIFF import requires version 2.1.");
        var locale = request.Mapping?.GetValueOrDefault("locale") ?? root.Attribute("trgLang")?.Value;
        if (string.IsNullOrWhiteSpace(locale)) throw new LocalizationImportFormatException("PKLI403", "XLIFF import requires trgLang or an explicit locale mapping.");
        var scope = request.Scope ?? new LocalizationScope(LocalizationScopeKind.Application);
        var entries = new List<LocalizationImportEntry>();
        var diagnostics = new List<LocalizationDiagnostic>();
        foreach (var unit in root.Descendants().Where(element => element.Name.LocalName == "unit"))
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (entries.Count >= options.MaximumRows) throw new LocalizationImportFormatException("PKLI404", "XLIFF unit limit exceeded.");
            var key = unit.Attribute("id")?.Value;
            var segment = unit.Descendants().FirstOrDefault(element => element.Name.LocalName == "segment");
            var source = segment?.Elements().FirstOrDefault(element => element.Name.LocalName == "source");
            var target = segment?.Elements().FirstOrDefault(element => element.Name.LocalName == "target");
            if (string.IsNullOrWhiteSpace(key) || source is null || target is null) { diagnostics.Add(new LocalizationDiagnostic("PKLI405", LocalizationDiagnosticSeverity.Error, "XLIFF unit requires id, source, and target.")); continue; }
            if (source.DescendantNodes().Any(node => node is XElement) || target.DescendantNodes().Any(node => node is XElement)) { diagnostics.Add(new LocalizationDiagnostic("PKLI406", LocalizationDiagnosticSeverity.Error, "XLIFF inline codes require an explicit application adapter and were not imported.", key, locale)); continue; }
            var pattern = target.Value;
            if (pattern.Length > options.MaximumCellCharacters || source.Value.Length > options.MaximumCellCharacters) throw new LocalizationImportFormatException("PKLI407", "XLIFF segment exceeds the configured character limit.");
            if (!string.IsNullOrWhiteSpace(pattern)) entries.Add(new LocalizationImportEntry(key, locale, scope, pattern, source.Value, Provenance: request.SourceName));
        }
        return ValueTask.FromResult(new LocalizationImportDocument(entries, diagnostics));
    }
}
