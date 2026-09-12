using System.Text.Json;

namespace Orbyss.Forms;

/// <summary>A typed, bounded comparison against one declared scalar field. Missing and null values never satisfy equality or inequality.</summary>
public sealed record FormCondition(string FieldId, FormConditionOperator Operator, JsonElement? Value = null)
{
    /// <summary>Evaluates a condition against object data and its immutable field declarations.</summary>
    public bool Evaluate(JsonElement data, IReadOnlyList<FormFieldDefinition> fields)
    {
        var field = fields.FirstOrDefault(item => item.Id == FieldId)
            ?? throw new InvalidOperationException($"Condition references unknown field '{FieldId}'.");
        var present = TryResolve(data, field.DataPath, out var actual) && actual.ValueKind != JsonValueKind.Null;
        if (Operator == FormConditionOperator.IsAbsent) return !present;
        if (Operator == FormConditionOperator.IsPresent) return present;
        if (!present || Value is not { } expected || !MatchesScalar(field.ValueKind, actual)) return false;
        var equal = actual.ValueKind switch
        {
            JsonValueKind.String => expected.ValueKind == JsonValueKind.String && actual.GetString() == expected.GetString(),
            JsonValueKind.True or JsonValueKind.False => actual.ValueKind == expected.ValueKind,
            JsonValueKind.Number => expected.ValueKind == JsonValueKind.Number && actual.GetDouble() == expected.GetDouble(),
            _ => false
        };
        return Operator == FormConditionOperator.Equals ? equal : Operator == FormConditionOperator.NotEquals && !equal;
    }

    /// <summary>Checks the supported scalar type without coercion.</summary>
    public static bool MatchesScalar(FormValueKind kind, JsonElement value) => kind switch
    {
        FormValueKind.String or FormValueKind.Date or FormValueKind.DateTime or FormValueKind.Time => value.ValueKind == JsonValueKind.String,
        FormValueKind.Boolean => value.ValueKind is JsonValueKind.True or JsonValueKind.False,
        FormValueKind.Number => value.ValueKind == JsonValueKind.Number && value.TryGetDouble(out var number) && double.IsFinite(number),
        FormValueKind.Integer => value.ValueKind == JsonValueKind.Number && value.TryGetDouble(out var integer) && double.IsFinite(integer) && Math.Truncate(integer) == integer,
        _ => false
    };

    /// <summary>Resolves a rooted object-only JSON Pointer; arrays are not traversed.</summary>
    public static bool TryResolve(JsonElement root, string pointer, out JsonElement value)
    {
        value = root;
        if (!pointer.StartsWith('/')) return false;
        foreach (var segment in pointer[1..].Split('/'))
        {
            if (value.ValueKind != JsonValueKind.Object || !value.TryGetProperty(segment.Replace("~1", "/", StringComparison.Ordinal).Replace("~0", "~", StringComparison.Ordinal), out value)) return false;
        }
        return true;
    }
}
