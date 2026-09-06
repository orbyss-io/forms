namespace ProgramKit.Localization;

/// <summary>Describes the base presentation direction for localized text.</summary>
public enum TextDirection
{
    /// <summary>Text flows from left to right.</summary>
    LeftToRight,
    /// <summary>Text flows from right to left.</summary>
    RightToLeft,
    /// <summary>The consumer derives direction from message metadata or first-strong text.</summary>
    Auto
}
