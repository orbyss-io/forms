namespace Orbyss.Localization;

/// <summary>Defines one typed placeholder accepted by a localized message.</summary>
public sealed record LocalizationArgumentDefinition(
    string Name,
    LocalizationArgumentType Type,
    bool Required = true);
