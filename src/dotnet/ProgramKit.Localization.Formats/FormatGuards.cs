using System.Security.Cryptography;

namespace ProgramKit.Localization.Formats;

/// <summary>Applies shared content and digest checks before any parser observes untrusted bytes.</summary>
internal static class FormatGuards
{
    /// <summary>Requires the selected format, positive limits, bounded content, and an optional matching digest.</summary>
    public static void RequireFormatAndBounds(LocalizationImportRequest request, LocalizationImportFormat format, LocalizationImportFormatOptions options)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (request.Format != format) throw new LocalizationImportFormatException("PKLI001", $"The {format} adapter cannot parse {request.Format} content.");
        if (request.Content.IsEmpty) throw new LocalizationImportFormatException("PKLI002", "Localization import content is empty.");
        if (request.Content.Length > options.MaximumContentBytes) throw new LocalizationImportFormatException("PKLI003", "Localization import content exceeds the configured byte limit.");
        if (request.ContentSha256 is not null)
        {
            if (request.ContentSha256.Length != 64 || request.ContentSha256.Any(character => !Uri.IsHexDigit(character))) throw new LocalizationImportFormatException("PKLI004", "Localization import content does not match its declared SHA-256 digest.");
            var actual = Convert.ToHexStringLower(SHA256.HashData(request.Content.Span));
            if (!CryptographicOperations.FixedTimeEquals(System.Text.Encoding.ASCII.GetBytes(actual), System.Text.Encoding.ASCII.GetBytes(request.ContentSha256.ToLowerInvariant())))
            {
                throw new LocalizationImportFormatException("PKLI004", "Localization import content does not match its declared SHA-256 digest.");
            }
        }
        if (options.MaximumRows < 1 || options.MaximumColumns < 1 || options.MaximumCellCharacters < 1 || options.MaximumArchiveEntries < 1 || options.MaximumExpandedBytes < 1)
        {
            throw new ArgumentOutOfRangeException(nameof(options), "Localization import limits must be positive.");
        }
    }
}
