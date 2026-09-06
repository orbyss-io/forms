using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ProgramKit.Localization;

/// <summary>Provides deterministic copies and versions for process-local storage.</summary>
internal static class InMemoryLocalizationStorageCodec
{
    /// <summary>Uses stable web serialization for cloning and version calculation.</summary>
    internal static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web);
    /// <summary>Creates a detached value so callers cannot mutate stored state through retained references.</summary>
    internal static T Clone<T>(T value) => JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Options), Options) ?? throw new InvalidDataException("The in-memory Localization document could not be cloned.");
    /// <summary>Computes a lowercase SHA-256 digest over stable JSON.</summary>
    internal static string Hash(object value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(value, Options))));
    /// <summary>Rejects a serialized document that exceeds its process-local memory budget.</summary>
    internal static void EnsureSize(object value, int maximumBytes)
    {
        if (Encoding.UTF8.GetByteCount(JsonSerializer.Serialize(value, Options)) > maximumBytes) throw new InvalidOperationException("The in-memory Localization document exceeds its configured size limit.");
    }
    /// <summary>Rejects unsafe process-local capacity bounds.</summary>
    internal static void Validate(InMemoryLocalizationStorageOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        if (options.MaximumDocuments is < 1 or > 1_000_000 || options.MaximumCommandsPerCatalog is < 1 or > 1_000_000 || options.MaximumDocumentBytes is < 1024 or > 268_435_456) throw new ArgumentOutOfRangeException(nameof(options), "In-memory Localization storage bounds are invalid.");
    }
}
