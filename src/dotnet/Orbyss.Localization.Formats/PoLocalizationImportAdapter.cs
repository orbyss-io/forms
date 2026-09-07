using System.Text;
using System.Text.Json;

namespace Orbyss.Localization.Formats;

/// <summary>Parses bounded singular GNU gettext PO entries without executing headers or extensions.</summary>
public sealed class PoLocalizationImportAdapter : ILocalizationImportFormatAdapter
{
    /// <summary>Bounds applied while decoding gettext input.</summary>
    private readonly LocalizationImportFormatOptions options;

    /// <summary>Initializes the PO adapter with secure defaults.</summary>
    public PoLocalizationImportAdapter(LocalizationImportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationImportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Po;

    /// <inheritdoc />
    public ValueTask<LocalizationImportDocument> ParseAsync(LocalizationImportRequest request, CancellationToken cancellationToken = default)
    {
        FormatGuards.RequireFormatAndBounds(request, Format, options);
        if (request.Mapping?.GetValueOrDefault("locale") is not { Length: > 0 } locale) throw new LocalizationImportFormatException("PKLI301", "PO import requires an explicit locale mapping.");
        string source;
        try { source = new UTF8Encoding(false, true).GetString(request.Content.Span); }
        catch (DecoderFallbackException) { throw new LocalizationImportFormatException("PKLI306", "PO content must be valid UTF-8."); }
        if (source.Length > 0 && source[0] == '\uFEFF') source = source[1..];
        var scope = request.Scope ?? new LocalizationScope(LocalizationScopeKind.Application);
        var entries = new List<LocalizationImportEntry>();
        var diagnostics = new List<LocalizationDiagnostic>();
        string? context = null, id = null, translation = null, active = null;
        var plural = false;
        foreach (var raw in source.Replace("\r\n", "\n", StringComparison.Ordinal).Split('\n').Append(string.Empty))
        {
            cancellationToken.ThrowIfCancellationRequested();
            var line = raw.Trim();
            if (line.Length == 0)
            {
                Flush(); context = null; id = null; translation = null; active = null; plural = false; continue;
            }
            if (line.StartsWith('#')) continue;
            if (line.StartsWith("msgctxt ", StringComparison.Ordinal)) { context = Decode(line[8..]); active = "context"; }
            else if (line.StartsWith("msgid_plural ", StringComparison.Ordinal)) { plural = true; active = "plural"; }
            else if (line.StartsWith("msgid ", StringComparison.Ordinal)) { id = Decode(line[6..]); active = "id"; }
            else if (line.StartsWith("msgstr[", StringComparison.Ordinal)) { plural = true; active = "plural"; }
            else if (line.StartsWith("msgstr ", StringComparison.Ordinal)) { translation = Decode(line[7..]); active = "translation"; }
            else if (line.StartsWith('"'))
            {
                var fragment = Decode(line);
                if (active == "context") context += fragment;
                else if (active == "id") id += fragment;
                else if (active == "translation") translation += fragment;
            }
            else throw new LocalizationImportFormatException("PKLI302", "PO content contains an unsupported directive.");
        }
        return ValueTask.FromResult(new LocalizationImportDocument(entries, diagnostics));

        void Flush()
        {
            if (id is not { Length: > 0 }) return;
            if (plural) { diagnostics.Add(new LocalizationDiagnostic("PKLI303", LocalizationDiagnosticSeverity.Error, "PO plural entries require an explicit application mapping to ICU and were not imported.", context ?? id, locale)); return; }
            if (string.IsNullOrWhiteSpace(translation)) return;
            if (id.Length > options.MaximumCellCharacters || translation.Length > options.MaximumCellCharacters || context?.Length > options.MaximumCellCharacters) throw new LocalizationImportFormatException("PKLI307", "PO entry exceeds the configured character limit.");
            if (entries.Count >= options.MaximumRows) throw new LocalizationImportFormatException("PKLI304", "PO entry limit exceeded.");
            entries.Add(new LocalizationImportEntry(context ?? id, locale, scope, translation, id, Provenance: request.SourceName));
        }
    }

    /// <summary>Decodes one PO quoted string with JSON-compatible escape semantics.</summary>
    private static string Decode(string value)
    {
        try { return JsonSerializer.Deserialize<string>(value) ?? string.Empty; }
        catch (JsonException) { throw new LocalizationImportFormatException("PKLI305", "PO content contains an invalid escaped string."); }
    }
}
