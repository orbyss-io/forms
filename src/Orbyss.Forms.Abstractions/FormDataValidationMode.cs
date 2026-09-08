namespace Orbyss.Forms;

/// <summary>Selects partial draft checks or authoritative submission checks.</summary>
public enum FormDataValidationMode
{
    /// <summary>Validate only supplied values and permit required values to remain absent.</summary>
    Draft,

    /// <summary>Validate all values and enforce every required form constraint.</summary>
    Submission
}
