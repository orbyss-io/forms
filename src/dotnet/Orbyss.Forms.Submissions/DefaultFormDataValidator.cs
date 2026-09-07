using System.Globalization;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Orbyss.Forms;

/// <summary>Validates runtime data against the provider-neutral field snapshot embedded in a form release.</summary>
public sealed class DefaultFormDataValidator : IFormDataValidator
{
    /// <inheritdoc />
    public ValueTask<IReadOnlyList<FormDataDiagnostic>> ValidateAsync(FormRelease release, FormDataDocument data, FormDataValidationMode mode, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(release);
        ArgumentNullException.ThrowIfNull(data);
        cancellationToken.ThrowIfCancellationRequested();
        var diagnostics = new List<FormDataDiagnostic>();
        using var document = JsonDocument.Parse(data.Json, new JsonDocumentOptions { MaxDepth = 64 });
        var fields = release.Candidate.Fields ?? throw new InvalidOperationException("The form release does not contain the provider-neutral field snapshot required for server validation.");
        foreach (var field in fields)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (!TryResolve(document.RootElement, field.DataPath, out var value))
            {
                if (mode == FormDataValidationMode.Submission && field.Required) diagnostics.Add(Error("PKFD001", "A required value is missing.", field.DataPath));
                continue;
            }
            ValidateValue(field, value, diagnostics);
        }
        return ValueTask.FromResult<IReadOnlyList<FormDataDiagnostic>>(diagnostics);
    }

    /// <summary>Checks one present value against its provider-neutral field contract.</summary>
    private static void ValidateValue(FormFieldDefinition field, JsonElement value, ICollection<FormDataDiagnostic> diagnostics)
    {
        if (!MatchesKind(field.ValueKind, value))
        {
            diagnostics.Add(Error("PKFD002", $"The value must be {field.ValueKind.ToString().ToLowerInvariant()}.", field.DataPath));
            return;
        }
        var constraints = field.Constraints;
        if (constraints is null) return;
        if (value.ValueKind == JsonValueKind.String)
        {
            var text = value.GetString() ?? string.Empty;
            CheckBounds(text.Length, constraints.MinimumLength, constraints.MaximumLength, field.DataPath, diagnostics, "text length");
            if (constraints.Pattern is not null && !Regex.IsMatch(text, constraints.Pattern, RegexOptions.CultureInvariant | RegexOptions.NonBacktracking, TimeSpan.FromMilliseconds(100))) diagnostics.Add(Error("PKFD005", "The value does not match the required pattern.", field.DataPath));
        }
        if (value.ValueKind == JsonValueKind.Array) CheckBounds(value.GetArrayLength(), constraints.MinimumItems, constraints.MaximumItems, field.DataPath, diagnostics, "item count");
        if (value.ValueKind == JsonValueKind.Number && value.TryGetDecimal(out var number))
        {
            if (constraints.Minimum is { } minimum && number < minimum) diagnostics.Add(Error("PKFD003", $"The value must be at least {minimum.ToString(CultureInfo.InvariantCulture)}.", field.DataPath));
            if (constraints.Maximum is { } maximum && number > maximum) diagnostics.Add(Error("PKFD004", $"The value must be at most {maximum.ToString(CultureInfo.InvariantCulture)}.", field.DataPath));
        }
        if (constraints.Choices is { Count: > 0 } choices && !choices.Any(choice => ChoiceMatches(choice.Value, value))) diagnostics.Add(Error("PKFD006", "The value is not an allowed choice.", field.DataPath));
    }

    /// <summary>Adds diagnostics when a collection or string violates length bounds.</summary>
    private static void CheckBounds(int length, int? minimum, int? maximum, string path, ICollection<FormDataDiagnostic> diagnostics, string noun)
    {
        if (minimum is { } minimumValue && length < minimumValue) diagnostics.Add(Error("PKFD003", $"The {noun} must be at least {minimumValue}.", path));
        if (maximum is { } maximumValue && length > maximumValue) diagnostics.Add(Error("PKFD004", $"The {noun} must be at most {maximumValue}.", path));
    }

    /// <summary>Checks JSON primitive and temporal-format compatibility.</summary>
    private static bool MatchesKind(FormValueKind kind, JsonElement value) => kind switch
    {
        FormValueKind.String => value.ValueKind == JsonValueKind.String,
        FormValueKind.Integer => value.ValueKind == JsonValueKind.Number && value.TryGetInt64(out _),
        FormValueKind.Number => value.ValueKind == JsonValueKind.Number,
        FormValueKind.Boolean => value.ValueKind is JsonValueKind.True or JsonValueKind.False,
        FormValueKind.Object => value.ValueKind == JsonValueKind.Object,
        FormValueKind.Array => value.ValueKind == JsonValueKind.Array,
        FormValueKind.Date => value.ValueKind == JsonValueKind.String && DateOnly.TryParseExact(value.GetString(), "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out _),
        FormValueKind.DateTime => value.ValueKind == JsonValueKind.String && DateTimeOffset.TryParse(value.GetString(), CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out _),
        FormValueKind.Time => value.ValueKind == JsonValueKind.String && TimeOnly.TryParse(value.GetString(), CultureInfo.InvariantCulture, DateTimeStyles.None, out _),
        _ => false
    };

    /// <summary>Compares one allowed string contract to a primitive JSON value.</summary>
    private static bool ChoiceMatches(string choice, JsonElement value) => value.ValueKind switch
    {
        JsonValueKind.String => string.Equals(choice, value.GetString(), StringComparison.Ordinal),
        JsonValueKind.Number => string.Equals(choice, value.GetRawText(), StringComparison.Ordinal),
        JsonValueKind.True => string.Equals(choice, "true", StringComparison.Ordinal),
        JsonValueKind.False => string.Equals(choice, "false", StringComparison.Ordinal),
        _ => false
    };

    /// <summary>Resolves a rooted object-only JSON Pointer without accepting array traversal.</summary>
    private static bool TryResolve(JsonElement root, string pointer, out JsonElement value)
    {
        value = root;
        if (string.IsNullOrEmpty(pointer) || pointer[0] != '/') return false;
        foreach (var encoded in pointer[1..].Split('/'))
        {
            if (value.ValueKind != JsonValueKind.Object || !value.TryGetProperty(encoded.Replace("~1", "/", StringComparison.Ordinal).Replace("~0", "~", StringComparison.Ordinal), out value)) return false;
        }
        return true;
    }

    /// <summary>Creates one blocking public-safe data diagnostic.</summary>
    private static FormDataDiagnostic Error(string code, string message, string path) => new(code, FormDiagnosticSeverity.Error, message, path);
}
