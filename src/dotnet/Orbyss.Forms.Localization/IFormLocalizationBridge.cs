namespace Orbyss.Forms.Localization;

/// <summary>Maps compiled form translation requirements into localization-owned catalog messages.</summary>
public interface IFormLocalizationBridge
{
    /// <summary>Produces a nonpersisted catalog revision while retaining all existing translation values.</summary>
    FormLocalizationMergeResult Merge(
        Orbyss.Forms.FormCandidate candidate,
        Orbyss.Localization.LocalizationCatalogDefinition catalog);
}
