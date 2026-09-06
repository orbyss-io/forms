using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ProgramKit.Forms;

/// <summary>Provides digest-verified, bounded and atomic JSON document persistence.</summary>
internal static class FileSystemVerifiedJson
{
    /// <summary>Uses stable web serialization for verified envelopes and versions.</summary>
    internal static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web) { WriteIndented = false };

    /// <summary>Computes a lowercase SHA-256 digest.</summary>
    internal static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    /// <summary>Reads, bounds, verifies, and deserializes an envelope.</summary>
    internal static async ValueTask<T> ReadAsync<T>(string path, int maximumBytes, CancellationToken cancellationToken)
    {
        var info = new FileInfo(path);
        if (info.Length > maximumBytes) throw new InvalidDataException($"Operational document '{path}' exceeds its configured limit.");
        var content = await File.ReadAllTextAsync(path, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
        var envelope = JsonNode.Parse(content)?.AsObject() ?? throw new InvalidDataException($"Operational document '{path}' is invalid JSON.");
        var payload = envelope["payload"]?.GetValue<string>() ?? throw new InvalidDataException($"Operational document '{path}' has no payload.");
        var digest = envelope["sha256"]?.GetValue<string>() ?? throw new InvalidDataException($"Operational document '{path}' has no digest.");
        if (!string.Equals(digest, Hash(payload), StringComparison.Ordinal)) throw new InvalidDataException($"Operational document '{path}' failed content verification.");
        return JsonSerializer.Deserialize<T>(payload, Options) ?? throw new InvalidDataException($"Operational document '{path}' has no typed payload.");
    }

    /// <summary>Serializes and atomically replaces one bounded digest envelope.</summary>
    internal static async ValueTask WriteAsync<T>(string path, T value, int maximumBytes, CancellationToken cancellationToken)
    {
        var payload = JsonSerializer.Serialize(value, Options);
        var envelope = new JsonObject { ["sha256"] = Hash(payload), ["payload"] = payload }.ToJsonString(Options);
        if (Encoding.UTF8.GetByteCount(envelope) > maximumBytes) throw new InvalidOperationException("The operational document exceeds its configured persistence limit.");
        var temporary = Path.Combine(Path.GetDirectoryName(path)!, $".{Path.GetFileName(path)}.{Guid.NewGuid():N}.tmp");
        try
        {
            await File.WriteAllTextAsync(temporary, envelope, Encoding.UTF8, cancellationToken).ConfigureAwait(false);
            File.Move(temporary, path, overwrite: true);
        }
        finally
        {
            if (File.Exists(temporary)) File.Delete(temporary);
        }
    }
}
