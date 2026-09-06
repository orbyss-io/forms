namespace ProgramKit.Forms;

/// <summary>Validates declared and observed attachment properties before trusted use.</summary>
public interface IFormAttachmentPolicy
{
    /// <summary>Gets the maximum accepted byte length for one attachment.</summary>
    long MaximumBytes { get; }

    /// <summary>Gets the number of leading bytes required for content-signature inspection.</summary>
    int InspectionPrefixBytes { get; }

    /// <summary>Validates the caller-declared name and media type before reading content.</summary>
    void ValidateDeclaration(string fileName, string mediaType);

    /// <summary>Validates measured length and leading content bytes after quarantine.</summary>
    void ValidateContent(string fileName, string mediaType, long length, ReadOnlySpan<byte> prefix);
}
