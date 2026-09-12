namespace Orbyss.Forms;

/// <summary>Defines portable comparisons for declarative field conditions and legacy visibility rules.</summary>
public enum FormConditionOperator
{
    /// <summary>The field equals the supplied value.</summary>
    Equals,
    /// <summary>The field does not equal the supplied value.</summary>
    NotEquals,
    /// <summary>The field is present; typed conditions mean an existing non-null value, including empty strings, zero and false.</summary>
    IsPresent,
    /// <summary>The field is absent; typed conditions include both missing and null values.</summary>
    IsAbsent
}
