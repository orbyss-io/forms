namespace ProgramKit.Localization;

/// <summary>Describes an argument accepted by a localized message.</summary>
public enum LocalizationArgumentType
{
    /// <summary>A Unicode text value.</summary>
    String,
    /// <summary>A locale-formatted numeric value.</summary>
    Number,
    /// <summary>A locale-formatted integer used for plural selection when requested.</summary>
    Integer,
    /// <summary>A locale-formatted date value.</summary>
    Date,
    /// <summary>A locale-formatted date and time value.</summary>
    DateTime,
    /// <summary>A locale-formatted time value.</summary>
    Time,
    /// <summary>A stable selector value.</summary>
    Select
}
