namespace ProgramKit.Forms;

/// <summary>Defines portable comparisons available to declarative visibility rules.</summary>
public enum FormConditionOperator
{
    /// <summary>The field equals the supplied value.</summary>
    Equals,
    /// <summary>The field does not equal the supplied value.</summary>
    NotEquals,
    /// <summary>The field has a nonempty value.</summary>
    IsPresent,
    /// <summary>The field has no value.</summary>
    IsAbsent
}
