using System.Security.Cryptography;

namespace Orbyss.Forms;

/// <summary>Provides bounded in-memory attachment quarantine for deterministic tests and local development.</summary>
public sealed class InMemoryFormAttachmentContentStore : IFormAttachmentContentStore
{
    /// <summary>Serializes content state and capacity accounting.</summary>
    private readonly object gate = new();
    /// <summary>Holds untrusted bytes awaiting a clean scan verdict.</summary>
    private readonly Dictionary<string, byte[]> quarantine = new(StringComparer.Ordinal);
    /// <summary>Holds scanner-approved bytes.</summary>
    private readonly Dictionary<string, byte[]> available = new(StringComparer.Ordinal);
    /// <summary>Bounds combined content retained by the process.</summary>
    private readonly long maximumTotalBytes;
    /// <summary>Bounds one buffered attachment object.</summary>
    private readonly long maximumObjectBytes;
    /// <summary>Tracks combined quarantined and available content bytes.</summary>
    private long totalBytes;

    /// <summary>Initializes an empty bounded content store.</summary>
    public InMemoryFormAttachmentContentStore(InMemoryFormStorageOptions? options = null)
    {
        var configured = options ?? new InMemoryFormStorageOptions(); InMemoryFormStorageCodec.Validate(configured); maximumTotalBytes = configured.MaximumAttachmentBytes; maximumObjectBytes = configured.MaximumAttachmentObjectBytes;
    }

    /// <inheritdoc />
    public async ValueTask<FormAttachmentContentWriteResult> WriteQuarantinedAsync(FormAttachmentId attachmentId, Stream content, long maximumBytes, int prefixBytes, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(attachmentId); ArgumentException.ThrowIfNullOrWhiteSpace(attachmentId.Value); ArgumentNullException.ThrowIfNull(content);
        if (maximumBytes < 1 || maximumBytes > maximumObjectBytes || prefixBytes < 1 || prefixBytes > 1_048_576) throw new ArgumentOutOfRangeException(nameof(maximumBytes));
        await using var buffer = new MemoryStream();
        using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        var block = new byte[81_920]; long length = 0;
        while (true)
        {
            var read = await content.ReadAsync(block, cancellationToken).ConfigureAwait(false); if (read == 0) break;
            length = checked(length + read); if (length > maximumBytes) throw new FormAttachmentRejectedException("size-not-allowed");
            hash.AppendData(block, 0, read); await buffer.WriteAsync(block.AsMemory(0, read), cancellationToken).ConfigureAwait(false);
        }
        var bytes = buffer.ToArray(); var key = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32));
        lock (gate)
        {
            if (totalBytes > maximumTotalBytes - bytes.LongLength) throw new FormAttachmentRejectedException("in-memory-capacity-exceeded");
            quarantine.Add(key, bytes); totalBytes += bytes.LongLength;
        }
        return new FormAttachmentContentWriteResult(key, length, Convert.ToHexStringLower(hash.GetHashAndReset()), bytes.AsMemory(0, Math.Min(prefixBytes, bytes.Length)));
    }

    /// <inheritdoc />
    public ValueTask<Stream> OpenQuarantinedAsync(string contentKey, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateKey(contentKey);
        lock (gate)
        {
            if (!quarantine.TryGetValue(contentKey, out var bytes) && !available.TryGetValue(contentKey, out bytes)) throw new KeyNotFoundException("The attachment content does not exist.");
            return ValueTask.FromResult<Stream>(new MemoryStream(bytes, writable: false));
        }
    }

    /// <inheritdoc />
    public ValueTask<string> PromoteAsync(string contentKey, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateKey(contentKey);
        lock (gate)
        {
            if (available.ContainsKey(contentKey)) return ValueTask.FromResult(contentKey);
            if (!quarantine.Remove(contentKey, out var bytes)) throw new KeyNotFoundException("The quarantined attachment content does not exist.");
            available.Add(contentKey, bytes); return ValueTask.FromResult(contentKey);
        }
    }

    /// <inheritdoc />
    public ValueTask<Stream> OpenAvailableAsync(string contentKey, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateKey(contentKey);
        lock (gate)
        {
            if (!available.TryGetValue(contentKey, out var bytes)) throw new KeyNotFoundException("The available attachment content does not exist.");
            return ValueTask.FromResult<Stream>(new MemoryStream(bytes, writable: false));
        }
    }

    /// <inheritdoc />
    public ValueTask DeleteAsync(string contentKey, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested(); ValidateKey(contentKey);
        lock (gate)
        {
            if (quarantine.Remove(contentKey, out var quarantined)) totalBytes -= quarantined.LongLength;
            if (available.Remove(contentKey, out var promoted)) totalBytes -= promoted.LongLength;
            return ValueTask.CompletedTask;
        }
    }

    /// <summary>Rejects keys not issued by this store.</summary>
    private static void ValidateKey(string key)
    {
        if (key.Length != 64 || key.Any(character => !char.IsAsciiHexDigit(character))) throw new InvalidOperationException("The attachment content key is invalid.");
    }
}
