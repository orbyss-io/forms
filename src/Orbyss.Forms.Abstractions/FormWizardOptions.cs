namespace Orbyss.Forms;

/// <summary>Defines portable wizard navigation, validation, persistence, and presentation policy.</summary>
public sealed record FormWizardOptions(
    FormWizardNavigationPolicy NavigationPolicy,
    FormWizardNavigationPlacement NavigationPlacement,
    FormWizardProgressStyle ProgressStyle,
    bool ValidateBeforeAdvance = true,
    bool SaveProgress = false,
    bool DeepLink = false);
