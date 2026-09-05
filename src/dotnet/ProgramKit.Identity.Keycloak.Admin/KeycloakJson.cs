using System.Text.Json;
using ProgramKit.Identity.Admin;

namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Projects Keycloak JSON representations into provider-neutral identity contracts.</summary>
internal static class KeycloakJson
{
    /// <summary>Projects a Keycloak user representation into its portable contract.</summary>
    public static IdentityUser User(JsonElement value) => new(
        String(value, "id"), String(value, "username"), OptionalString(value, "email"),
        OptionalString(value, "firstName"), OptionalString(value, "lastName"),
        Boolean(value, "enabled"), Boolean(value, "emailVerified"), Attributes(value));

    /// <summary>Projects a Keycloak client representation into its portable contract.</summary>
    public static IdentityApplication Application(JsonElement value) => new(
        String(value, "id"), String(value, "clientId"), OptionalString(value, "name"),
        Boolean(value, "enabled"), Boolean(value, "publicClient"),
        Strings(value, "redirectUris"), Strings(value, "webOrigins"));

    /// <summary>Projects a Keycloak client-scope representation into its portable contract.</summary>
    public static IdentityScope Scope(JsonElement value) => new(
        String(value, "id"), String(value, "name"), OptionalString(value, "description"));

    /// <summary>Projects a Keycloak role representation into its portable contract.</summary>
    public static IdentityRole Role(JsonElement value) => new(
        String(value, "id"), String(value, "name"), OptionalString(value, "description"), Boolean(value, "composite"));

    /// <summary>Projects a Keycloak group representation into its portable contract.</summary>
    public static IdentityGroup Group(JsonElement value) => new(
        String(value, "id"), String(value, "name"), OptionalString(value, "path"));

    /// <summary>Projects a Keycloak credential representation into its portable contract.</summary>
    public static IdentityCredential Credential(JsonElement value) => new(
        String(value, "id"), String(value, "type"), OptionalString(value, "userLabel"), OptionalInt64(value, "createdDate"));

    /// <summary>Projects a Keycloak session representation into its portable contract.</summary>
    public static IdentitySession Session(JsonElement value)
    {
        var clients = value.TryGetProperty("clients", out var clientObject) && clientObject.ValueKind == JsonValueKind.Object
            ? clientObject.EnumerateObject().Select(item => item.Value.GetString() ?? item.Name).ToArray()
            : [];
        return new(String(value, "id"), String(value, "userId"), OptionalString(value, "ipAddress"),
            OptionalInt64(value, "start"), OptionalInt64(value, "lastAccess"), clients);
    }

    /// <summary>Maps an optional JSON array to an immutable portable result list.</summary>
    public static IReadOnlyList<T> Array<T>(JsonElement? value, Func<JsonElement, T> map)
    {
        if (value is not { ValueKind: JsonValueKind.Array } array)
        {
            return [];
        }
        return array.EnumerateArray().Select(map).ToArray();
    }

    /// <summary>Reads a string property or returns an empty portable fallback.</summary>
    public static string String(JsonElement value, string property) =>
        value.TryGetProperty(property, out var found) && found.ValueKind == JsonValueKind.String
            ? found.GetString() ?? string.Empty
            : string.Empty;

    /// <summary>Reads an optional string property.</summary>
    public static string? OptionalString(JsonElement value, string property) =>
        value.TryGetProperty(property, out var found) && found.ValueKind == JsonValueKind.String ? found.GetString() : null;

    /// <summary>Reads a boolean property with a false fallback.</summary>
    private static bool Boolean(JsonElement value, string property) =>
        value.TryGetProperty(property, out var found) && found.ValueKind == JsonValueKind.True;

    /// <summary>Reads an optional 64-bit integer property.</summary>
    private static long? OptionalInt64(JsonElement value, string property) =>
        value.TryGetProperty(property, out var found) && found.TryGetInt64(out var result) ? result : null;

    /// <summary>Reads a string-array property with an empty fallback.</summary>
    private static string[] Strings(JsonElement value, string property) =>
        value.TryGetProperty(property, out var found) && found.ValueKind == JsonValueKind.Array
            ? found.EnumerateArray().Select(item => item.GetString()).Where(item => item is not null).Cast<string>().ToArray()
            : [];

    /// <summary>Projects Keycloak's multi-valued user attributes.</summary>
    private static IReadOnlyDictionary<string, string[]> Attributes(JsonElement value)
    {
        if (!value.TryGetProperty("attributes", out var attributes) || attributes.ValueKind != JsonValueKind.Object)
        {
            return new Dictionary<string, string[]>();
        }
        return attributes.EnumerateObject().ToDictionary(
            property => property.Name,
            property => property.Value.ValueKind == JsonValueKind.Array
                ? property.Value.EnumerateArray().Select(item => item.GetString()).Where(item => item is not null).Cast<string>().ToArray()
                : [],
            StringComparer.Ordinal);
    }
}
