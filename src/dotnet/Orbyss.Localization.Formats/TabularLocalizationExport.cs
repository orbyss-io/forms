using System.Text.Json;
using System.Text.Json.Serialization;

namespace Orbyss.Localization.Formats;

/// <summary>Projects normalized entries into deterministic wide rows with explicit scope columns.</summary>
internal static class TabularLocalizationExport
{
    /// <summary>Stable compact JSON settings for typed ICU argument metadata.</summary>
    private static readonly JsonSerializerOptions ArgumentJson = new(JsonSerializerDefaults.Web) { Converters = { new JsonStringEnumConverter() } };

    /// <summary>Creates a header and one row per scoped message for the selected target locales.</summary>
    public static IReadOnlyList<IReadOnlyList<string>> CreateRows(
        LocalizationExportRequest request,
        IReadOnlyList<LocalizationExportEntry> entries,
        LocalizationExportFormatOptions options)
    {
        var locales = (request.LanguageTags ?? request.Catalog.Locales.Where(locale => !string.Equals(locale.LanguageTag, request.Catalog.SourceLocale, StringComparison.OrdinalIgnoreCase)).Select(locale => locale.LanguageTag).ToArray())
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(languageTag => languageTag, StringComparer.OrdinalIgnoreCase)
            .ToArray();
        var header = new[] { "scopeKind", "parentResourceId", "resourceId", "key", "source", "arguments", "description", "context" }.Concat(locales).ToArray();
        if (header.Length > options.MaximumColumns) throw new LocalizationImportFormatException("PKLE008", "Localization tabular export column limit exceeded.");
        var rows = new List<IReadOnlyList<string>> { header };
        foreach (var group in entries.GroupBy(entry => (entry.Scope, entry.Key)))
        {
            var first = group.First();
            var values = group.ToDictionary(entry => entry.LanguageTag, entry => entry.Pattern, StringComparer.OrdinalIgnoreCase);
            rows.Add(new[] { first.Scope.Kind.ToString(), first.Scope.ParentResourceId ?? string.Empty, first.Scope.ResourceId ?? string.Empty, first.Key, first.SourcePattern, JsonSerializer.Serialize(first.Arguments, ArgumentJson), first.Description ?? string.Empty, first.Context ?? string.Empty }.Concat(locales.Select(locale => values.GetValueOrDefault(locale) ?? string.Empty)).ToArray());
        }
        if (rows.SelectMany(row => row).Any(cell => cell.Length > options.MaximumCellCharacters)) throw new LocalizationImportFormatException("PKLE009", "Localization tabular export cell limit exceeded.");
        return rows;
    }
}
