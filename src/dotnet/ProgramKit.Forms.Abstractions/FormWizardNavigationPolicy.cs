namespace ProgramKit.Forms;

/// <summary>Controls which wizard steps a user may select directly.</summary>
public enum FormWizardNavigationPolicy
{
    /// <summary>Only sequential navigation is allowed.</summary>
    Linear,
    /// <summary>Previously visited steps may be selected.</summary>
    Visited,
    /// <summary>Any enabled visible step may be selected.</summary>
    NonLinear
}
