using System.Security.Cryptography;
using System.Text;

namespace Orbyss.Localization.Formats;

/// <summary>Validates export selection and creates bounded digest-bearing results.</summary>
internal static class ExportGuards
{
    /// <summary>Validates format, catalog, limits, locales, and optional single-scope requirements.</summary>
    public static IReadOnlyList<LocalizationExportEntry> Project(
        LocalizationExportRequest request,
        LocalizationImportFormat format,
        LocalizationExportFormatOptions options,
        bool requireSingleLocale = false,
        bool requireScope = false)
    {
        ArgumentNullException.ThrowIfNull(request);
        ArgumentNullException.ThrowIfNull(request.Catalog);
        if (request.Format != format) throw new LocalizationImportFormatException("PKLE001", $"The {format} adapter cannot export {request.Format} content.");
        if (options.MaximumContentBytes < 1 || options.MaximumRows < 1 || options.MaximumColumns < 1 || options.MaximumCellCharacters < 1) throw new ArgumentOutOfRangeException(nameof(options), "Localization export limits must be positive.");
        if (requireScope && request.Scope is null) throw new LocalizationImportFormatException("PKLE002", $"{format} export requires one explicit scope to avoid ambiguous message identities.");
        var declared = request.Catalog.Locales.Select(locale => locale.LanguageTag).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var selected = (request.LanguageTags ?? request.Catalog.Locales.Where(locale => !string.Equals(locale.LanguageTag, request.Catalog.SourceLocale, StringComparison.OrdinalIgnoreCase)).Select(locale => locale.LanguageTag).ToArray()).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        if (selected.Length == 0 || selected.Any(languageTag => !declared.Contains(languageTag))) throw new LocalizationImportFormatException("PKLE003", "Export locale selection is empty or contains an undeclared locale.");
        if (requireSingleLocale && selected.Length != 1) throw new LocalizationImportFormatException("PKLE004", $"{format} export requires exactly one target locale.");
        var localeSet = selected.ToHashSet(StringComparer.OrdinalIgnoreCase);
        var entries = request.Catalog.Messages
            .Where(message => request.Scope is null || message.Scope == request.Scope)
            .SelectMany(message => message.Values.Where(value => localeSet.Contains(value.LanguageTag)).Select(value => new LocalizationExportEntry(message.Key, value.LanguageTag, message.Scope, message.SourcePattern, value.Pattern, message.Arguments, message.Description, message.Context, value.Provenance)))
            .OrderBy(entry => ScopeIdentity(entry.Scope), StringComparer.Ordinal)
            .ThenBy(entry => entry.Key, StringComparer.Ordinal)
            .ThenBy(entry => entry.LanguageTag, StringComparer.OrdinalIgnoreCase)
            .ToArray();
        if (entries.Length > options.MaximumRows) throw new LocalizationImportFormatException("PKLE005", "Localization export row limit exceeded.");
        foreach (var entry in entries) if (Fields(entry).Any(field => field?.Length > options.MaximumCellCharacters)) throw new LocalizationImportFormatException("PKLE006", "Localization export contains a value over the configured character limit.");
        return entries;
    }

    /// <summary>Builds a bounded export result and computes its lowercase SHA-256 digest.</summary>
    public static LocalizationExportDocument Document(
        LocalizationImportFormat format,
        byte[] content,
        string mediaType,
        string extension,
        LocalizationExportRequest request,
        LocalizationExportFormatOptions options)
    {
        if (content.Length > options.MaximumContentBytes) throw new LocalizationImportFormatException("PKLE007", "Localization export exceeds the configured byte limit.");
        var baseName = string.IsNullOrWhiteSpace(request.SuggestedBaseName) ? request.Catalog.Id.Value : request.SuggestedBaseName;
        var safeName = string.Concat(baseName!.Select(character => char.IsAsciiLetterOrDigit(character) || character is '-' or '_' or '.' ? character : '-')).Trim('.', '-');
        if (safeName.Length == 0) safeName = "localization";
        return new LocalizationExportDocument(format, content, mediaType, $"{safeName}.{extension}", Convert.ToHexStringLower(SHA256.HashData(content)));
    }

    /// <summary>Creates a stable structured-scope identity for deterministic ordering.</summary>
    public static string ScopeIdentity(LocalizationScope scope) => $"{scope.Kind}:{scope.ParentResourceId}:{scope.ResourceId}";

    /// <summary>Enumerates all bounded text carried by one normalized export entry.</summary>
    private static IEnumerable<string?> Fields(LocalizationExportEntry entry) =>
        [entry.Key, entry.LanguageTag, entry.Scope.ResourceId, entry.Scope.ParentResourceId, entry.SourcePattern, entry.Pattern, entry.Description, entry.Context, entry.Provenance, .. entry.Arguments.Select(argument => argument.Name)];
}
