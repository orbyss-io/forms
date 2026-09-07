namespace Orbyss.Localization;

/// <summary>Describes the owner represented by a localization scope.</summary>
public enum LocalizationScopeKind
{
    /// <summary>Messages shared across the application.</summary>
    Application,
    /// <summary>Messages owned by an application feature.</summary>
    Feature,
    /// <summary>Messages owned by one form.</summary>
    Form,
    /// <summary>Validation messages owned by one form.</summary>
    FormValidation,
    /// <summary>A consumer-defined scope with an explicit owner.</summary>
    Custom
}
