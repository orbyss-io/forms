namespace ProgramKit.Localization;

/// <summary>Describes the review state of a translated value.</summary>
public enum LocalizationValueState
{
    /// <summary>The value is an incomplete human draft.</summary>
    Draft,
    /// <summary>The value was suggested by an automated provider and requires review.</summary>
    MachineSuggested,
    /// <summary>The value has received human review.</summary>
    Reviewed,
    /// <summary>The value is approved for publication.</summary>
    Approved
}
