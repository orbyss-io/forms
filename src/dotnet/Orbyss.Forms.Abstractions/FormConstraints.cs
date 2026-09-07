namespace Orbyss.Forms;

/// <summary>Defines portable value constraints that a compiler maps to its validation target.</summary>
public sealed record FormConstraints(
    decimal? Minimum = null,
    decimal? Maximum = null,
    int? MinimumLength = null,
    int? MaximumLength = null,
    int? MinimumItems = null,
    int? MaximumItems = null,
    string? Pattern = null,
    IReadOnlyList<FormChoiceDefinition>? Choices = null);
