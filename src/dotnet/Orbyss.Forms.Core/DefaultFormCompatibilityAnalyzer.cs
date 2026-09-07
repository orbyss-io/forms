namespace Orbyss.Forms;

/// <summary>Classifies data-contract, renderer, action, and presentation changes between releases.</summary>
public sealed class DefaultFormCompatibilityAnalyzer : IFormCompatibilityAnalyzer
{
    /// <inheritdoc />
    public ValueTask<FormCompatibilityReport> AnalyzeAsync(
        FormRelease baseline,
        FormCandidate candidate,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(baseline);
        ArgumentNullException.ThrowIfNull(candidate);
        cancellationToken.ThrowIfCancellationRequested();

        if (baseline.Candidate.FormId != candidate.FormId)
        {
            throw new ArgumentException("The baseline and candidate must belong to the same form.", nameof(candidate));
        }

        var issues = new List<FormCompatibilityIssue>();
        CompareFields(baseline.Candidate, candidate, issues);
        CompareRenderers(baseline.Candidate.Renderers, candidate.Renderers, issues);
        CompareActions(baseline.Candidate.Actions, candidate.Actions, issues);
        if (!string.Equals(baseline.Candidate.UiSchema.Sha256, candidate.UiSchema.Sha256, StringComparison.Ordinal)
            && issues.All(issue => issue.Code != "PKFC200"))
        {
            issues.Add(new FormCompatibilityIssue("PKFC200", FormCompatibilityImpact.Compatible, "The presentation artifact changed.", "/uiSchema"));
        }

        return ValueTask.FromResult(new FormCompatibilityReport(baseline.Id, candidate.Revision, issues));
    }

    /// <summary>Classifies semantic field changes and falls back to artifact review for legacy candidates.</summary>
    private static void CompareFields(
        FormCandidate baseline,
        FormCandidate candidate,
        ICollection<FormCompatibilityIssue> issues)
    {
        if (baseline.Fields is null || candidate.Fields is null)
        {
            if (!string.Equals(baseline.DataSchema.Sha256, candidate.DataSchema.Sha256, StringComparison.Ordinal))
            {
                issues.Add(new FormCompatibilityIssue(
                    "PKFC100",
                    FormCompatibilityImpact.Review,
                    "The data contract changed without a semantic field manifest; manual review is required.",
                    "/dataSchema"));
            }

            return;
        }

        var oldFields = baseline.Fields.ToDictionary(field => field.Id, StringComparer.Ordinal);
        var newFields = candidate.Fields.ToDictionary(field => field.Id, StringComparer.Ordinal);
        foreach (var oldField in oldFields.Values)
        {
            if (!newFields.TryGetValue(oldField.Id, out var newField))
            {
                issues.Add(Breaking("PKFC101", $"Field '{oldField.Id}' was removed.", oldField.DataPath));
                continue;
            }

            if (!string.Equals(oldField.DataPath, newField.DataPath, StringComparison.Ordinal))
            {
                issues.Add(Breaking("PKFC102", $"Field '{oldField.Id}' moved from '{oldField.DataPath}' to '{newField.DataPath}'.", newField.DataPath));
            }

            if (oldField.ValueKind != newField.ValueKind)
            {
                issues.Add(Breaking("PKFC103", $"Field '{oldField.Id}' changed value kind.", newField.DataPath));
            }

            if (!oldField.Required && newField.Required)
            {
                issues.Add(Breaking("PKFC104", $"Field '{oldField.Id}' became required.", newField.DataPath));
            }

            CompareConstraints(oldField, newField, issues);
        }

        foreach (var newField in newFields.Values.Where(field => !oldFields.ContainsKey(field.Id)))
        {
            issues.Add(new FormCompatibilityIssue(
                newField.Required ? "PKFC105" : "PKFC106",
                newField.Required ? FormCompatibilityImpact.Breaking : FormCompatibilityImpact.Compatible,
                $"{(newField.Required ? "Required" : "Optional")} field '{newField.Id}' was added.",
                newField.DataPath));
        }
    }

    /// <summary>Classifies newly tightened accepted-value constraints as migration-requiring.</summary>
    private static void CompareConstraints(
        FormFieldDefinition oldField,
        FormFieldDefinition newField,
        ICollection<FormCompatibilityIssue> issues)
    {
        var oldConstraints = oldField.Constraints;
        var newConstraints = newField.Constraints;
        if (newConstraints is null)
        {
            return;
        }

        if (GreaterThan(newConstraints.Minimum, oldConstraints?.Minimum)
            || LessThan(newConstraints.Maximum, oldConstraints?.Maximum)
            || GreaterThan(newConstraints.MinimumLength, oldConstraints?.MinimumLength)
            || LessThan(newConstraints.MaximumLength, oldConstraints?.MaximumLength)
            || GreaterThan(newConstraints.MinimumItems, oldConstraints?.MinimumItems)
            || LessThan(newConstraints.MaximumItems, oldConstraints?.MaximumItems)
            || PatternChanged(oldConstraints?.Pattern, newConstraints.Pattern)
            || ChoicesRemoved(oldConstraints?.Choices, newConstraints.Choices))
        {
            issues.Add(Breaking("PKFC107", $"Field '{newField.Id}' has stricter accepted values.", newField.DataPath));
        }
    }

    /// <summary>Marks new or changed renderer dependencies for consumer review.</summary>
    private static void CompareRenderers(
        IReadOnlyList<FormRendererRequirement> baseline,
        IReadOnlyList<FormRendererRequirement> candidate,
        ICollection<FormCompatibilityIssue> issues)
    {
        var existing = baseline.ToDictionary(renderer => renderer.ComponentId, StringComparer.Ordinal);
        foreach (var renderer in candidate)
        {
            if (!existing.TryGetValue(renderer.ComponentId, out var oldRenderer))
            {
                issues.Add(new FormCompatibilityIssue("PKFC200", FormCompatibilityImpact.Review, $"Renderer '{renderer.ComponentId}' is newly required.", "/renderers"));
            }
            else if (!string.Equals(oldRenderer.VersionRange, renderer.VersionRange, StringComparison.Ordinal))
            {
                issues.Add(new FormCompatibilityIssue("PKFC201", FormCompatibilityImpact.Review, $"Renderer '{renderer.ComponentId}' changed its version requirement.", "/renderers"));
            }
        }
    }

    /// <summary>Marks removed or rebound application actions for consumer review.</summary>
    private static void CompareActions(
        IReadOnlyList<FormActionRequirement> baseline,
        IReadOnlyList<FormActionRequirement> candidate,
        ICollection<FormCompatibilityIssue> issues)
    {
        var current = candidate.ToDictionary(action => action.ActionId, StringComparer.Ordinal);
        foreach (var action in baseline)
        {
            if (!current.TryGetValue(action.ActionId, out var newAction))
            {
                issues.Add(new FormCompatibilityIssue("PKFC300", FormCompatibilityImpact.Review, $"Action '{action.ActionId}' was removed.", "/actions"));
            }
            else if (action.Kind != newAction.Kind || !string.Equals(action.HandlerId, newAction.HandlerId, StringComparison.Ordinal))
            {
                issues.Add(new FormCompatibilityIssue("PKFC301", FormCompatibilityImpact.Review, $"Action '{action.ActionId}' changed its handler contract.", "/actions"));
            }
        }
    }

    /// <summary>Returns whether a nullable lower bound became stricter.</summary>
    private static bool GreaterThan<T>(T? candidate, T? baseline)
        where T : struct, IComparable<T> =>
        candidate.HasValue && (!baseline.HasValue || candidate.Value.CompareTo(baseline.Value) > 0);

    /// <summary>Returns whether a nullable upper bound became stricter.</summary>
    private static bool LessThan<T>(T? candidate, T? baseline)
        where T : struct, IComparable<T> =>
        candidate.HasValue && (!baseline.HasValue || candidate.Value.CompareTo(baseline.Value) < 0);

    /// <summary>Returns whether a candidate introduces or changes a pattern constraint.</summary>
    private static bool PatternChanged(string? baseline, string? candidate) =>
        candidate is not null && !string.Equals(baseline, candidate, StringComparison.Ordinal);

    /// <summary>Returns whether a candidate removes any previously accepted choice value.</summary>
    private static bool ChoicesRemoved(
        IReadOnlyList<FormChoiceDefinition>? baseline,
        IReadOnlyList<FormChoiceDefinition>? candidate)
    {
        if (baseline is null || candidate is null)
        {
            return false;
        }

        var current = candidate.Select(choice => choice.Value).ToHashSet(StringComparer.Ordinal);
        return baseline.Any(choice => !current.Contains(choice.Value));
    }

    /// <summary>Creates a stable migration-requiring compatibility finding.</summary>
    private static FormCompatibilityIssue Breaking(string code, string message, string path) =>
        new(code, FormCompatibilityImpact.Breaking, message, path);
}
