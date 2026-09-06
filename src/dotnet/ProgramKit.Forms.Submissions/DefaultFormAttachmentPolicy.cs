namespace ProgramKit.Forms;

/// <summary>Applies a strict media-type, extension, size, and magic-byte allowlist.</summary>
public sealed class DefaultFormAttachmentPolicy : IFormAttachmentPolicy
{
    /// <summary>Maps normalized allowed media types to their extension and signature contracts.</summary>
    private readonly IReadOnlyDictionary<string, AllowedFormAttachmentType> allowed;

    /// <summary>Initializes a fail-closed attachment policy.</summary>
    public DefaultFormAttachmentPolicy(FormAttachmentPolicyOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        if (options.MaximumBytes is < 1 or > 1_073_741_824) throw new ArgumentOutOfRangeException(nameof(options), "The attachment limit must be between 1 byte and 1 GiB.");
        if (options.InspectionPrefixBytes is < 16 or > 65_536) throw new ArgumentOutOfRangeException(nameof(options), "The inspection prefix must be between 16 bytes and 64 KiB.");
        if (options.AllowedTypes is null || options.AllowedTypes.Count == 0) throw new ArgumentException("At least one attachment type must be explicitly allowed.", nameof(options));
        allowed = options.AllowedTypes.ToDictionary(item => NormalizeMediaType(item.MediaType), ValidateType, StringComparer.Ordinal);
        MaximumBytes = options.MaximumBytes;
        InspectionPrefixBytes = options.InspectionPrefixBytes;
    }

    /// <inheritdoc />
    public long MaximumBytes { get; }

    /// <inheritdoc />
    public int InspectionPrefixBytes { get; }

    /// <inheritdoc />
    public void ValidateDeclaration(string fileName, string mediaType)
    {
        var name = SafeFileName(fileName);
        var normalizedMediaType = NormalizeMediaType(mediaType);
        if (!allowed.TryGetValue(normalizedMediaType, out var definition)) throw new FormAttachmentRejectedException("media-type-not-allowed");
        var extension = Path.GetExtension(name);
        if (string.IsNullOrWhiteSpace(extension) || !definition.Extensions.Contains(extension, StringComparer.OrdinalIgnoreCase)) throw new FormAttachmentRejectedException("extension-mismatch");
    }

    /// <inheritdoc />
    public void ValidateContent(string fileName, string mediaType, long length, ReadOnlySpan<byte> prefix)
    {
        ValidateDeclaration(fileName, mediaType);
        if (length is < 1 || length > MaximumBytes) throw new FormAttachmentRejectedException("size-not-allowed");
        var definition = allowed[NormalizeMediaType(mediaType)];
        var matches = false;
        foreach (var signature in definition.Signatures)
        {
            if (prefix.StartsWith(signature.Span)) { matches = true; break; }
        }
        if (!matches) throw new FormAttachmentRejectedException("content-signature-mismatch");
    }

    /// <summary>Validates and normalizes one configured allowlist entry.</summary>
    private static AllowedFormAttachmentType ValidateType(AllowedFormAttachmentType value)
    {
        if (value.Extensions is null || value.Extensions.Count == 0 || value.Extensions.Any(item => item.Length is < 2 or > 16 || item[0] != '.' || item.Any(character => !char.IsAsciiLetterOrDigit(character) && character != '.'))) throw new ArgumentException("Attachment extensions must be explicit short dot-prefixed values.");
        if (value.Signatures is null || value.Signatures.Count == 0 || value.Signatures.Any(item => item.Length is < 2 or > 4096)) throw new ArgumentException("Each allowed attachment type requires at least one bounded magic-byte signature.");
        return value with { MediaType = NormalizeMediaType(value.MediaType) };
    }

    /// <summary>Rejects directory components, invalid characters, and oversized names.</summary>
    private static string SafeFileName(string fileName)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(fileName);
        if (fileName.Length > 255 || !string.Equals(fileName, Path.GetFileName(fileName), StringComparison.Ordinal) || fileName.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0) throw new FormAttachmentRejectedException("unsafe-file-name");
        return fileName;
    }

    /// <summary>Removes parameters and normalizes a syntactically bounded media type.</summary>
    private static string NormalizeMediaType(string mediaType)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(mediaType);
        var normalized = mediaType.Split(';', 2)[0].Trim().ToLowerInvariant();
        if (normalized.Length is < 3 or > 127 || !normalized.Contains('/', StringComparison.Ordinal)) throw new FormAttachmentRejectedException("invalid-media-type");
        return normalized;
    }
}
