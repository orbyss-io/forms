using System.Text.Json;

namespace ProgramKit.Localization.Formats;

/// <summary>Parses the bounded Program Kit JSON localization interchange representation.</summary>
public sealed class JsonLocalizationImportAdapter : ILocalizationImportFormatAdapter
{
    /// <summary>Bounds applied while decoding JSON input.</summary>
    private readonly LocalizationImportFormatOptions options;

    /// <summary>Initializes the JSON adapter with secure defaults.</summary>
    public JsonLocalizationImportAdapter(LocalizationImportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationImportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Json;

    /// <inheritdoc />
    public ValueTask<LocalizationImportDocument> ParseAsync(LocalizationImportRequest request, CancellationToken cancellationToken = default)
    {
        FormatGuards.RequireFormatAndBounds(request, Format, options);
        cancellationToken.ThrowIfCancellationRequested();
        try
        {
            using var document = JsonDocument.Parse(request.Content, new JsonDocumentOptions { AllowTrailingCommas = false, CommentHandling = JsonCommentHandling.Disallow, MaxDepth = 32 });
            var root = document.RootElement;
            RequireProperties(root, "entries");
            if (!root.TryGetProperty("entries", out var values) || values.ValueKind != JsonValueKind.Array) throw new LocalizationImportFormatException("PKLI201", "JSON import requires an entries array.");
            if (values.GetArrayLength() > options.MaximumRows) throw new LocalizationImportFormatException("PKLI202", "JSON import row limit exceeded.");
            var entries = new List<LocalizationImportEntry>();
            var diagnostics = new List<LocalizationDiagnostic>();
            foreach (var value in values.EnumerateArray())
            {
                cancellationToken.ThrowIfCancellationRequested();
                RequireProperties(value, "key", "languageTag", "pattern", "sourcePattern", "scope", "arguments", "description", "context", "provenance");
                var key = RequiredString(value, "key");
                var locale = RequiredString(value, "languageTag");
                var pattern = RequiredString(value, "pattern");
                var scope = value.TryGetProperty("scope", out var scopeValue) ? ParseScope(scopeValue, options) : request.Scope ?? new LocalizationScope(LocalizationScopeKind.Application);
                var arguments = value.TryGetProperty("arguments", out var argumentValues) ? ParseArguments(argumentValues, options) : [];
                var sourcePattern = OptionalString(value, "sourcePattern");
                var description = OptionalString(value, "description");
                var context = OptionalString(value, "context");
                var provenance = OptionalString(value, "provenance") ?? request.SourceName;
                EnsureLength(key, options, "key");
                EnsureLength(locale, options, "languageTag");
                EnsureLength(pattern, options, "pattern");
                EnsureLength(sourcePattern, options, "sourcePattern");
                EnsureLength(description, options, "description");
                EnsureLength(context, options, "context");
                EnsureLength(provenance, options, "provenance");
                entries.Add(new LocalizationImportEntry(
                    key,
                    locale,
                    scope,
                    pattern,
                    sourcePattern,
                    arguments,
                    description,
                    context,
                    provenance));
            }
            return ValueTask.FromResult(new LocalizationImportDocument(entries, diagnostics));
        }
        catch (JsonException)
        {
            throw new LocalizationImportFormatException("PKLI203", "JSON localization content is malformed or exceeds the nesting limit.");
        }
    }

    /// <summary>Maps an allowlisted JSON scope object to the provider-neutral contract.</summary>
    private static LocalizationScope ParseScope(JsonElement value, LocalizationImportFormatOptions options)
    {
        RequireProperties(value, "kind", "resourceId", "parentResourceId");
        if (!Enum.TryParse<LocalizationScopeKind>(RequiredString(value, "kind"), true, out var kind)) throw new LocalizationImportFormatException("PKLI204", "JSON localization scope kind is invalid.");
        var resourceId = OptionalString(value, "resourceId");
        var parentResourceId = OptionalString(value, "parentResourceId");
        EnsureLength(resourceId, options, "scope resourceId");
        EnsureLength(parentResourceId, options, "scope parentResourceId");
        return new LocalizationScope(kind, resourceId, parentResourceId);
    }

    /// <summary>Maps bounded ICU argument declarations from the JSON representation.</summary>
    private static IReadOnlyList<LocalizationArgumentDefinition> ParseArguments(JsonElement values, LocalizationImportFormatOptions options)
    {
        if (values.ValueKind != JsonValueKind.Array) throw new LocalizationImportFormatException("PKLI205", "JSON localization arguments must be an array.");
        if (values.GetArrayLength() > options.MaximumColumns) throw new LocalizationImportFormatException("PKLI211", "JSON localization argument limit exceeded.");
        var result = new List<LocalizationArgumentDefinition>();
        foreach (var value in values.EnumerateArray())
        {
            RequireProperties(value, "name", "type", "required");
            if (!Enum.TryParse<LocalizationArgumentType>(RequiredString(value, "type"), true, out var type)) throw new LocalizationImportFormatException("PKLI206", "JSON localization argument type is invalid.");
            var name = RequiredString(value, "name");
            EnsureLength(name, options, "argument name");
            var isRequired = true;
            if (value.TryGetProperty("required", out var required))
            {
                if (required.ValueKind is not (JsonValueKind.True or JsonValueKind.False)) throw new LocalizationImportFormatException("PKLI212", "JSON localization argument 'required' must be boolean.");
                isRequired = required.GetBoolean();
            }
            result.Add(new LocalizationArgumentDefinition(name, type, isRequired));
        }
        return result;
    }

    /// <summary>Returns a required non-blank string property.</summary>
    private static string RequiredString(JsonElement value, string name) =>
        value.TryGetProperty(name, out var property) && property.ValueKind == JsonValueKind.String && !string.IsNullOrWhiteSpace(property.GetString())
            ? property.GetString()!
            : throw new LocalizationImportFormatException("PKLI207", $"JSON localization property '{name}' is required.");

    /// <summary>Returns an optional string property while rejecting type coercion.</summary>
    private static string? OptionalString(JsonElement value, string name) =>
        value.TryGetProperty(name, out var property) && property.ValueKind != JsonValueKind.Null
            ? property.ValueKind == JsonValueKind.String ? property.GetString() : throw new LocalizationImportFormatException("PKLI208", $"JSON localization property '{name}' must be text.")
            : null;

    /// <summary>Rejects non-object values and properties outside the explicit interchange schema.</summary>
    private static void RequireProperties(JsonElement value, params string[] allowed)
    {
        if (value.ValueKind != JsonValueKind.Object) throw new LocalizationImportFormatException("PKLI209", "JSON localization values must be objects.");
        var names = new HashSet<string>(allowed, StringComparer.Ordinal);
        foreach (var property in value.EnumerateObject()) if (!names.Contains(property.Name)) throw new LocalizationImportFormatException("PKLI210", $"JSON localization property '{property.Name}' is not allowed.");
    }

    /// <summary>Rejects text values that exceed the configured per-cell ceiling.</summary>
    private static void EnsureLength(string? value, LocalizationImportFormatOptions options, string name)
    {
        if (value?.Length > options.MaximumCellCharacters) throw new LocalizationImportFormatException("PKLI213", $"JSON localization {name} exceeds the configured character limit.");
    }
}
