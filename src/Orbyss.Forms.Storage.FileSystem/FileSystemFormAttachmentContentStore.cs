using System.Security.Cryptography;

namespace Orbyss.Forms;

/// <summary>Stores attachment bytes under opaque keys in separate quarantine and available directories.</summary>
public sealed class FileSystemFormAttachmentContentStore : IFormAttachmentContentStore
{
    /// <summary>Holds untrusted bytes that have not received a clean verdict.</summary>
    private readonly string quarantineDirectory;
    /// <summary>Holds content promoted after signature and malware checks.</summary>
    private readonly string availableDirectory;

    /// <summary>Initializes content storage below one explicit consumer-owned directory.</summary>
    public FileSystemFormAttachmentContentStore(FileSystemFormOperationalStoreOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        ArgumentException.ThrowIfNullOrWhiteSpace(options.DirectoryPath);
        var root = Path.GetFullPath(options.DirectoryPath);
        quarantineDirectory = Path.Combine(root, "attachment-quarantine");
        availableDirectory = Path.Combine(root, "attachment-available");
        Directory.CreateDirectory(quarantineDirectory);
        Directory.CreateDirectory(availableDirectory);
    }

    /// <inheritdoc />
    public async ValueTask<FormAttachmentContentWriteResult> WriteQuarantinedAsync(FormAttachmentId attachmentId, Stream content, long maximumBytes, int prefixBytes, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(attachmentId);
        ArgumentNullException.ThrowIfNull(content);
        if (maximumBytes < 1 || prefixBytes < 1) throw new ArgumentOutOfRangeException(nameof(maximumBytes));
        var key = FileSystemVerifiedJson.Hash(attachmentId.Value + ":" + Guid.NewGuid().ToString("N"));
        var path = QuarantinePath(key);
        var prefix = new byte[prefixBytes];
        var prefixLength = 0;
        long length = 0;
        using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        var buffer = new byte[81_920];
        try
        {
            await using var output = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None, buffer.Length, FileOptions.Asynchronous | FileOptions.WriteThrough);
            while (true)
            {
                var read = await content.ReadAsync(buffer, cancellationToken).ConfigureAwait(false);
                if (read == 0) break;
                length = checked(length + read);
                if (length > maximumBytes) throw new FormAttachmentRejectedException("size-not-allowed");
                hash.AppendData(buffer, 0, read);
                if (prefixLength < prefix.Length)
                {
                    var copy = Math.Min(read, prefix.Length - prefixLength);
                    Buffer.BlockCopy(buffer, 0, prefix, prefixLength, copy);
                    prefixLength += copy;
                }
                await output.WriteAsync(buffer.AsMemory(0, read), cancellationToken).ConfigureAwait(false);
            }
            await output.FlushAsync(cancellationToken).ConfigureAwait(false);
        }
        catch
        {
            if (File.Exists(path)) File.Delete(path);
            throw;
        }
        return new FormAttachmentContentWriteResult(key, length, Convert.ToHexStringLower(hash.GetHashAndReset()), prefix.AsMemory(0, prefixLength));
    }

    /// <inheritdoc />
    public ValueTask<Stream> OpenQuarantinedAsync(string contentKey, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var quarantine = QuarantinePath(contentKey);
        var path = File.Exists(quarantine) ? quarantine : AvailablePath(contentKey);
        return ValueTask.FromResult<Stream>(new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 81_920, FileOptions.Asynchronous | FileOptions.SequentialScan));
    }

    /// <inheritdoc />
    public ValueTask<string> PromoteAsync(string contentKey, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var source = QuarantinePath(contentKey);
        var target = AvailablePath(contentKey);
        if (File.Exists(target)) return ValueTask.FromResult(contentKey);
        File.Move(source, target, overwrite: false);
        return ValueTask.FromResult(contentKey);
    }

    /// <inheritdoc />
    public ValueTask<Stream> OpenAvailableAsync(string contentKey, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return ValueTask.FromResult<Stream>(new FileStream(AvailablePath(contentKey), FileMode.Open, FileAccess.Read, FileShare.Read, 81_920, FileOptions.Asynchronous | FileOptions.SequentialScan));
    }

    /// <inheritdoc />
    public ValueTask DeleteAsync(string contentKey, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var quarantine = QuarantinePath(contentKey);
        var available = AvailablePath(contentKey);
        if (File.Exists(quarantine)) File.Delete(quarantine);
        if (File.Exists(available)) File.Delete(available);
        return ValueTask.CompletedTask;
    }

    /// <summary>Maps an opaque key to its quarantine path.</summary>
    private string QuarantinePath(string key) => Path.Combine(quarantineDirectory, SafeKey(key) + ".bin");
    /// <summary>Maps an opaque key to its promoted path.</summary>
    private string AvailablePath(string key) => Path.Combine(availableDirectory, SafeKey(key) + ".bin");
    /// <summary>Rejects keys that were not issued by this store.</summary>
    private static string SafeKey(string key)
    {
        if (key.Length != 64 || key.Any(character => !char.IsAsciiHexDigit(character))) throw new InvalidOperationException("The attachment content key is invalid.");
        return key.ToLowerInvariant();
    }
}
