using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ProgramKit.Forms;

/// <summary>Prevents mutable references from escaping the in-memory persistence boundary.</summary>
internal static class InMemoryFormStorageCodec
{
    /// <summary>Uses stable web serialization for cloning and version calculation.</summary>
    internal static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web);
    /// <summary>Creates a detached value so caller-owned mutable collections cannot alter stored state.</summary>
    internal static T Clone<T>(T value) => JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Options), Options) ?? throw new InvalidDataException("The in-memory Forms document could not be cloned.");
    /// <summary>Computes a lowercase SHA-256 digest over stable JSON.</summary>
    internal static string Hash(object value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(value, Options))));
    /// <summary>Rejects a serialized aggregate that exceeds its process-local memory budget.</summary>
    internal static void EnsureSize(object value, int maximumBytes)
    {
        if (Encoding.UTF8.GetByteCount(JsonSerializer.Serialize(value, Options)) > maximumBytes) throw new InvalidOperationException("The in-memory Forms document exceeds its configured size limit.");
    }
    /// <summary>Rejects unsafe process-local capacity bounds.</summary>
    internal static void Validate(InMemoryFormStorageOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        if (options.MaximumDocuments is < 1 or > 1_000_000) throw new ArgumentOutOfRangeException(nameof(options), "The in-memory Forms document count is invalid.");
        if (options.MaximumCommandsPerDocument is < 1 or > 1_000_000) throw new ArgumentOutOfRangeException(nameof(options), "The in-memory Forms command count is invalid.");
        if (options.MaximumDocumentBytes is < 1024 or > 268_435_456) throw new ArgumentOutOfRangeException(nameof(options), "The in-memory Forms document size is invalid.");
        if (options.MaximumAttachmentObjectBytes is < 1 or > 268_435_456) throw new ArgumentOutOfRangeException(nameof(options), "The in-memory attachment object size is invalid.");
        if (options.MaximumAttachmentBytes < options.MaximumAttachmentObjectBytes || options.MaximumAttachmentBytes > 4_294_967_296) throw new ArgumentOutOfRangeException(nameof(options), "The in-memory total attachment size is invalid.");
    }
}
