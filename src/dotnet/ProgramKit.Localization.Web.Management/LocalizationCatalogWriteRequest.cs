namespace ProgramKit.Localization.Web.Management;

/// <summary>Combines a catalog document with its governed mutation envelope.</summary>
public sealed record LocalizationCatalogWriteRequest(
    LocalizationCatalogDefinition Catalog,
    LocalizationWebMutation Mutation);
