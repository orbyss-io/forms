namespace Orbyss.Localization.Formats;

/// <summary>Reports a stable public-safe interchange parsing failure.</summary>
public sealed class LocalizationImportFormatException : Exception
{
    /// <summary>Initializes a format failure with a stable machine-readable code.</summary>
    public LocalizationImportFormatException(string code, string message)
        : base(message)
    {
        Code = code;
    }

    /// <summary>Gets the stable failure code.</summary>
    public string Code { get; }
}
