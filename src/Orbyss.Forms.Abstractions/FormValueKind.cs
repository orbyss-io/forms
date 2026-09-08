namespace Orbyss.Forms;

/// <summary>Describes a form value independently from a JSON Schema dialect.</summary>
public enum FormValueKind
{
    /// <summary>A Unicode text value.</summary>
    String,
    /// <summary>A whole-number value.</summary>
    Integer,
    /// <summary>A decimal numeric value.</summary>
    Number,
    /// <summary>A true-or-false value.</summary>
    Boolean,
    /// <summary>A calendar date without a time.</summary>
    Date,
    /// <summary>A date and time value.</summary>
    DateTime,
    /// <summary>A time without a date.</summary>
    Time,
    /// <summary>A structured object value.</summary>
    Object,
    /// <summary>An ordered collection value.</summary>
    Array
}
