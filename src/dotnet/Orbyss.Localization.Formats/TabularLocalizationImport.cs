using System.Text.Json;
using System.Text.Json.Serialization;

namespace Orbyss.Localization.Formats;

/// <summary>Maps bounded tabular rows into long or wide provider-neutral localization entries.</summary>
internal static class TabularLocalizationImport
{
    /// <summary>Column names that describe structure rather than locale values.</summary>
    private static readonly HashSet<string> Reserved = new(["key", "source", "sourceLocale", "locale", "pattern", "scopeKind", "resourceId", "parentResourceId", "arguments", "description", "context", "sheet"], StringComparer.OrdinalIgnoreCase);
    /// <summary>Strict compact JSON settings used by the tabular typed-argument column.</summary>
    private static readonly JsonSerializerOptions ArgumentJson = new(JsonSerializerDefaults.Web) { MaxDepth = 8, UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow, Converters = { new JsonStringEnumConverter() } };

    /// <summary>Maps bounded rows using either long locale/pattern columns or wide locale columns.</summary>
    public static LocalizationImportDocument Parse(
        IReadOnlyList<IReadOnlyList<string>> rows,
        LocalizationImportRequest request,
        LocalizationImportFormatOptions options)
    {
        if (rows.Count == 0) throw new LocalizationImportFormatException("PKLI110", "The import table is empty.");
        var headers = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        for (var index = 0; index < rows[0].Count; index++)
        {
            var header = rows[0][index].Trim();
            if (header.Length == 0) throw new LocalizationImportFormatException("PKLI116", "Tabular import contains a blank column name.");
            if (!headers.TryAdd(header, index)) throw new LocalizationImportFormatException("PKLI117", $"Tabular import repeats column '{header}'.");
        }
        var mapping = request.Mapping ?? new Dictionary<string, string>();
        var keyColumn = Column(headers, mapping, "key", "key", required: true);
        var sourceColumn = Column(headers, mapping, "source", "source", required: false);
        var localeColumn = Column(headers, mapping, "locale", "locale", required: false);
        var patternColumn = Column(headers, mapping, "pattern", "pattern", required: false);
        var scopeKindColumn = Column(headers, mapping, "scopeKind", "scopeKind", required: false);
        var resourceIdColumn = Column(headers, mapping, "resourceId", "resourceId", required: false);
        var parentResourceIdColumn = Column(headers, mapping, "parentResourceId", "parentResourceId", required: false);
        var argumentsColumn = Column(headers, mapping, "arguments", "arguments", required: false);
        var descriptionColumn = Column(headers, mapping, "description", "description", required: false);
        var contextColumn = Column(headers, mapping, "context", "context", required: false);
        var diagnostics = new List<LocalizationDiagnostic>();
        var entries = new List<LocalizationImportEntry>();
        var wideLocales = mapping
            .Where(item => !Reserved.Contains(item.Key) && IsLocale(item.Key))
            .Select(item => (Locale: item.Key, Column: Column(headers, mapping, item.Key, item.Value, required: true)!.Value))
            .ToArray();
        if (localeColumn is null || patternColumn is null)
        {
            if (wideLocales.Length == 0)
            {
                wideLocales = headers.Keys
                    .Where(header => !Reserved.Contains(header) && IsLocale(header) && !string.Equals(header, request.Mapping?.GetValueOrDefault("sourceLocale"), StringComparison.OrdinalIgnoreCase))
                    .Select(header => (Locale: header, Column: headers[header]))
                    .ToArray();
            }
            if (wideLocales.Length == 0) throw new LocalizationImportFormatException("PKLI111", "Tabular import requires locale/pattern columns or at least one locale-named value column.");
        }

        for (var rowIndex = 1; rowIndex < rows.Count; rowIndex++)
        {
            var row = rows[rowIndex];
            var key = Cell(row, keyColumn!.Value).Trim();
            if (key.Length == 0) { diagnostics.Add(Error("PKLI112", "A tabular row has no message key.")); continue; }
            var source = sourceColumn is null ? null : Cell(row, sourceColumn.Value);
            var scope = ParseScope(row, request.Scope, scopeKindColumn, resourceIdColumn, parentResourceIdColumn);
            var arguments = argumentsColumn is null ? null : ParseArguments(Cell(row, argumentsColumn.Value), options);
            var description = descriptionColumn is null ? null : EmptyToNull(Cell(row, descriptionColumn.Value));
            var context = contextColumn is null ? null : EmptyToNull(Cell(row, contextColumn.Value));
            if (localeColumn is not null && patternColumn is not null)
            {
                Add(entries, diagnostics, key, Cell(row, localeColumn.Value), Cell(row, patternColumn.Value), scope, source, arguments, description, context, request.SourceName);
            }
            else
            {
                foreach (var locale in wideLocales) Add(entries, diagnostics, key, locale.Locale, Cell(row, locale.Column), scope, source, arguments, description, context, request.SourceName);
            }
            if (entries.Count > options.MaximumRows) throw new LocalizationImportFormatException("PKLI113", "Expanded localization entry limit exceeded.");
        }
        return new LocalizationImportDocument(entries, diagnostics);
    }

    /// <summary>Resolves a semantic column role through explicit mapping and fallback name.</summary>
    private static int? Column(IReadOnlyDictionary<string, int> headers, IReadOnlyDictionary<string, string> mapping, string role, string fallback, bool required)
    {
        var name = mapping.GetValueOrDefault(role) ?? fallback;
        if (headers.TryGetValue(name, out var index)) return index;
        if (required) throw new LocalizationImportFormatException("PKLI114", $"Mapped column '{name}' was not found.");
        return null;
    }

    /// <summary>Returns a cell or an empty value for a sparse row.</summary>
    private static string Cell(IReadOnlyList<string> row, int index) => index < row.Count ? row[index] : string.Empty;

    /// <summary>Reads an optional structured scope from row columns or uses the requested scope.</summary>
    private static LocalizationScope ParseScope(
        IReadOnlyList<string> row,
        LocalizationScope? requested,
        int? kindColumn,
        int? resourceColumn,
        int? parentColumn)
    {
        if (kindColumn is null) return requested ?? new LocalizationScope(LocalizationScopeKind.Application);
        var value = Cell(row, kindColumn.Value);
        if (!Enum.TryParse<LocalizationScopeKind>(value, true, out var kind)) throw new LocalizationImportFormatException("PKLI118", $"Tabular scope kind '{value}' is invalid.");
        var resourceId = resourceColumn is null ? null : EmptyToNull(Cell(row, resourceColumn.Value));
        var parentResourceId = parentColumn is null ? null : EmptyToNull(Cell(row, parentColumn.Value));
        var scope = new LocalizationScope(kind, resourceId, parentResourceId);
        if (requested is not null && scope != requested) throw new LocalizationImportFormatException("PKLI119", "Tabular row scope does not match the requested import scope.");
        return scope;
    }

    /// <summary>Adds a non-blank localized pattern after locale validation.</summary>
    private static void Add(ICollection<LocalizationImportEntry> entries, ICollection<LocalizationDiagnostic> diagnostics, string key, string locale, string pattern, LocalizationScope scope, string? source, IReadOnlyList<LocalizationArgumentDefinition>? arguments, string? description, string? context, string? provenance)
    {
        if (!IsLocale(locale)) { diagnostics.Add(Error("PKLI115", $"Locale '{locale}' is invalid.", key, locale)); return; }
        if (string.IsNullOrWhiteSpace(pattern)) return;
        entries.Add(new LocalizationImportEntry(key, locale, scope, pattern, source, arguments, description, context, provenance));
    }

    /// <summary>Recognizes bounded BCP 47-shaped language tags without performing culture resolution.</summary>
    private static bool IsLocale(string value) => System.Text.RegularExpressions.Regex.IsMatch(value, "^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$", System.Text.RegularExpressions.RegexOptions.CultureInvariant);

    /// <summary>Creates a row-scoped blocking import diagnostic.</summary>
    private static LocalizationDiagnostic Error(string code, string message, string? key = null, string? locale = null) => new(code, LocalizationDiagnosticSeverity.Error, message, key, locale);

    /// <summary>Normalizes a blank optional tabular cell to no value.</summary>
    private static string? EmptyToNull(string value) => string.IsNullOrWhiteSpace(value) ? null : value;

    /// <summary>Parses the bounded optional typed-argument JSON column.</summary>
    private static IReadOnlyList<LocalizationArgumentDefinition> ParseArguments(string value, LocalizationImportFormatOptions options)
    {
        if (string.IsNullOrWhiteSpace(value)) return [];
        try
        {
            var arguments = JsonSerializer.Deserialize<LocalizationArgumentDefinition[]>(value, ArgumentJson) ?? [];
            if (arguments.Length > options.MaximumColumns) throw new LocalizationImportFormatException("PKLI120", "Tabular argument limit exceeded.");
            return arguments;
        }
        catch (JsonException)
        {
            throw new LocalizationImportFormatException("PKLI121", "Tabular arguments must use the bounded Orbyss Forms JSON representation.");
        }
    }
}
