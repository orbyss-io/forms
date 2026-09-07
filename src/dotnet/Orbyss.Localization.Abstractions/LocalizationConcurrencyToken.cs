namespace Orbyss.Localization;

/// <summary>Represents an opaque localization version used for optimistic concurrency.</summary>
public sealed record LocalizationConcurrencyToken(string Value);
