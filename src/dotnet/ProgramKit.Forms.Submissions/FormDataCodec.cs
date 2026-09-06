using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ProgramKit.Forms;

/// <summary>Creates stable, bounded form data documents for persistence and fingerprints.</summary>
internal static class FormDataCodec
{
    /// <summary>Parses an object document, orders its properties recursively, and computes its digest.</summary>
    internal static FormDataDocument Create(string json, int maximumBytes)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(json);
        if (Encoding.UTF8.GetByteCount(json) > maximumBytes) throw new InvalidOperationException("Form data exceeds the configured byte limit.");
        using var parsed = JsonDocument.Parse(json, new JsonDocumentOptions { MaxDepth = 64, CommentHandling = JsonCommentHandling.Disallow, AllowTrailingCommas = false });
        if (parsed.RootElement.ValueKind != JsonValueKind.Object) throw new InvalidOperationException("Form data must be a JSON object.");
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream)) WriteCanonical(writer, parsed.RootElement);
        var canonical = Encoding.UTF8.GetString(stream.ToArray());
        return new FormDataDocument(canonical, Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(canonical))));
    }

    /// <summary>Writes deterministic JSON with ordinally ordered object members.</summary>
    private static void WriteCanonical(Utf8JsonWriter writer, JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                writer.WriteStartObject();
                foreach (var property in element.EnumerateObject().OrderBy(item => item.Name, StringComparer.Ordinal))
                {
                    writer.WritePropertyName(property.Name);
                    WriteCanonical(writer, property.Value);
                }
                writer.WriteEndObject();
                break;
            case JsonValueKind.Array:
                writer.WriteStartArray();
                foreach (var item in element.EnumerateArray()) WriteCanonical(writer, item);
                writer.WriteEndArray();
                break;
            default:
                element.WriteTo(writer);
                break;
        }
    }
}
