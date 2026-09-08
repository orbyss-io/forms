using System.Text.RegularExpressions;

namespace Orbyss.Forms;

/// <summary>Applies deterministic structural, referential, and bounded-complexity validation.</summary>
public sealed class FormDefinitionValidator : IFormDefinitionValidator
{
    /// <summary>Holds the enforced limits for untrusted authoring input.</summary>
    private readonly FormValidationOptions options;

    /// <summary>Initializes a validator with secure default complexity limits.</summary>
    public FormDefinitionValidator()
        : this(new FormValidationOptions())
    {
    }

    /// <summary>Initializes a validator with explicit complexity limits.</summary>
    public FormDefinitionValidator(FormValidationOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        ValidateOptions(options);
        this.options = options;
    }

    /// <inheritdoc />
    public ValueTask<IReadOnlyList<FormDiagnostic>> ValidateAsync(
        FormDefinition definition,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(definition);
        cancellationToken.ThrowIfCancellationRequested();

        var diagnostics = new List<FormDiagnostic>();
        ValidateIdentity(definition, diagnostics);
        var translationDefaults = new Dictionary<string, string>(StringComparer.Ordinal);
        var fields = ValidateFields(definition.Fields, translationDefaults, diagnostics, cancellationToken);
        ValidateActions(definition.Actions, translationDefaults, diagnostics);
        var actionIds = definition.Actions
            .Where(action => !string.IsNullOrWhiteSpace(action.Id))
            .Select(action => action.Id)
            .ToHashSet(StringComparer.Ordinal);
        var placements = new Dictionary<string, int>(StringComparer.Ordinal);
        var elementIds = new HashSet<string>(StringComparer.Ordinal);
        var elementCount = 0;
        ValidateElement(
            definition.Layout,
            fields,
            translationDefaults,
            placements,
            elementIds,
            actionIds,
            diagnostics,
            parentKind: null,
            depth: 1,
            ref elementCount,
            cancellationToken);
        ValidateFieldPlacement(fields, placements, diagnostics);

        return ValueTask.FromResult<IReadOnlyList<FormDiagnostic>>(diagnostics);
    }

    /// <summary>Rejects nonsensical limits before they can disable bounded validation.</summary>
    private static void ValidateOptions(FormValidationOptions options)
    {
        if (options.MaximumFields <= 0
            || options.MaximumElements <= 0
            || options.MaximumLayoutDepth <= 0
            || options.MaximumChoicesPerField <= 0
            || options.MaximumPatternLength <= 0
            || options.MaximumOptionCount <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(options), "All form validation limits must be positive.");
        }
    }

    /// <summary>Validates the stable aggregate identity and source-language metadata.</summary>
    private static void ValidateIdentity(FormDefinition definition, ICollection<FormDiagnostic> diagnostics)
    {
        AddRequired(definition.Id.Value, "PKF001", "A form identifier is required.", "/id", diagnostics);
        AddRequired(definition.Name, "PKF002", "A form name is required.", "/name", diagnostics);
        AddRequired(definition.SourceLocale, "PKF003", "A source locale is required.", "/sourceLocale", diagnostics);
        if (definition.Revision.Value <= 0)
        {
            diagnostics.Add(Error("PKF004", "The form revision must be positive.", "/revision"));
        }

        if (!string.IsNullOrWhiteSpace(definition.SourceLocale) && !IsLocaleTag(definition.SourceLocale))
        {
            diagnostics.Add(Error("PKF005", "The source locale must be a bounded BCP 47 language tag.", "/sourceLocale"));
        }
    }

    /// <summary>Validates field identities, data paths, constraints, and component requests.</summary>
    private IReadOnlyDictionary<string, FormFieldDefinition> ValidateFields(
        IReadOnlyList<FormFieldDefinition> fields,
        IDictionary<string, string> translationDefaults,
        ICollection<FormDiagnostic> diagnostics,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(fields);
        if (fields.Count > options.MaximumFields)
        {
            diagnostics.Add(Error("PKF010", $"A form cannot contain more than {options.MaximumFields} fields.", "/fields"));
        }

        var byId = new Dictionary<string, FormFieldDefinition>(StringComparer.Ordinal);
        var paths = new HashSet<string>(StringComparer.Ordinal);
        for (var index = 0; index < fields.Count; index++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var field = fields[index];
            var path = $"/fields/{index}";
            AddRequired(field.Id, "PKF011", "A field identifier is required.", $"{path}/id", diagnostics);
            if (!string.IsNullOrWhiteSpace(field.Id) && !byId.TryAdd(field.Id, field))
            {
                diagnostics.Add(Error("PKF012", $"Field identifier '{field.Id}' is duplicated.", $"{path}/id"));
            }

            if (!IsJsonPointer(field.DataPath))
            {
                diagnostics.Add(Error("PKF013", "A field data path must be a rooted JSON Pointer with valid escapes and nonempty segments.", $"{path}/dataPath"));
            }
            else if (!paths.Add(field.DataPath))
            {
                diagnostics.Add(Error("PKF014", $"Data path '{field.DataPath}' is duplicated.", $"{path}/dataPath"));
            }

            ValidateText(field.Label, $"{path}/label", diagnostics);
            TrackTranslation(field.Label, translationDefaults, $"{path}/label", diagnostics);
            if (field.Description is not null)
            {
                ValidateText(field.Description, $"{path}/description", diagnostics);
                TrackTranslation(field.Description, translationDefaults, $"{path}/description", diagnostics);
            }

            ValidateConstraints(field, path, diagnostics);
            if (field.Constraints?.Choices is { } choices)
            {
                for (var choiceIndex = 0; choiceIndex < choices.Count; choiceIndex++)
                {
                    TrackTranslation(choices[choiceIndex].Label, translationDefaults, $"{path}/constraints/choices/{choiceIndex}/label", diagnostics);
                }
            }
            if (field.Component is not null)
            {
                AddRequired(field.Component.ComponentId, "PKF015", "A component identifier is required.", $"{path}/component/componentId", diagnostics);
                AddRequired(field.Component.VersionRange, "PKF016", "A component version range is required.", $"{path}/component/versionRange", diagnostics);
                if (field.Component.Options?.Count > options.MaximumOptionCount)
                {
                    diagnostics.Add(Error("PKF017", $"A component cannot have more than {options.MaximumOptionCount} options.", $"{path}/component/options"));
                }
            }
        }

        return byId;
    }

    /// <summary>Validates ordered bounds, safe patterns, and unique bounded choices.</summary>
    private void ValidateConstraints(FormFieldDefinition field, string path, ICollection<FormDiagnostic> diagnostics)
    {
        var constraints = field.Constraints;
        if (constraints is null)
        {
            return;
        }

        if (constraints.Minimum > constraints.Maximum)
        {
            diagnostics.Add(Error("PKF020", "The minimum cannot exceed the maximum.", $"{path}/constraints"));
        }

        var numeric = field.ValueKind is FormValueKind.Integer or FormValueKind.Number;
        if (!numeric && (constraints.Minimum.HasValue || constraints.Maximum.HasValue))
        {
            diagnostics.Add(Error("PKF028", "Numeric bounds can only be applied to integer or number fields.", $"{path}/constraints"));
        }

        if (field.ValueKind != FormValueKind.String
            && (constraints.MinimumLength.HasValue || constraints.MaximumLength.HasValue || constraints.Pattern is not null))
        {
            diagnostics.Add(Error("PKF029", "Text length and pattern constraints can only be applied to string fields.", $"{path}/constraints"));
        }

        if (field.ValueKind != FormValueKind.Array
            && (constraints.MinimumItems.HasValue || constraints.MaximumItems.HasValue))
        {
            diagnostics.Add(Error("PKF029A", "Collection size constraints can only be applied to array fields.", $"{path}/constraints"));
        }

        if (field.ValueKind is (FormValueKind.Object or FormValueKind.Array) && constraints.Choices is { Count: > 0 })
        {
            diagnostics.Add(Error("PKF029B", "Choices can only be applied to scalar fields.", $"{path}/constraints/choices"));
        }

        if (constraints.MinimumLength is < 0 || constraints.MaximumLength is < 0 || constraints.MinimumLength > constraints.MaximumLength)
        {
            diagnostics.Add(Error("PKF021", "Text length limits must be nonnegative and ordered.", $"{path}/constraints"));
        }

        if (constraints.MinimumItems is < 0 || constraints.MaximumItems is < 0 || constraints.MinimumItems > constraints.MaximumItems)
        {
            diagnostics.Add(Error("PKF022", "Collection size limits must be nonnegative and ordered.", $"{path}/constraints"));
        }

        if (constraints.Pattern is { } pattern)
        {
            if (pattern.Length > options.MaximumPatternLength)
            {
                diagnostics.Add(Error("PKF023", $"A pattern cannot exceed {options.MaximumPatternLength} characters.", $"{path}/constraints/pattern"));
            }
            else
            {
                try
                {
                    _ = new Regex(pattern, RegexOptions.CultureInvariant | RegexOptions.NonBacktracking, TimeSpan.FromMilliseconds(100));
                }
                catch (ArgumentException)
                {
                    diagnostics.Add(Error("PKF024", "The pattern must be valid for the bounded non-backtracking engine.", $"{path}/constraints/pattern"));
                }
            }
        }

        if (constraints.Choices is not { } choices)
        {
            return;
        }

        if (choices.Count > options.MaximumChoicesPerField)
        {
            diagnostics.Add(Error("PKF025", $"A field cannot contain more than {options.MaximumChoicesPerField} choices.", $"{path}/constraints/choices"));
        }

        var values = new HashSet<string>(StringComparer.Ordinal);
        for (var index = 0; index < choices.Count; index++)
        {
            var choice = choices[index];
            AddRequired(choice.Value, "PKF026", "A choice value is required.", $"{path}/constraints/choices/{index}/value", diagnostics);
            if (!string.IsNullOrWhiteSpace(choice.Value) && !values.Add(choice.Value))
            {
                diagnostics.Add(Error("PKF027", $"Choice value '{choice.Value}' is duplicated.", $"{path}/constraints/choices/{index}/value"));
            }

            ValidateText(choice.Label, $"{path}/constraints/choices/{index}/label", diagnostics);
        }
    }

    /// <summary>Walks the layout once while enforcing depth, size, references, and translation consistency.</summary>
    private void ValidateElement(
        FormElementDefinition element,
        IReadOnlyDictionary<string, FormFieldDefinition> fields,
        IDictionary<string, string> translationDefaults,
        IDictionary<string, int> placements,
        ISet<string> elementIds,
        IReadOnlySet<string> actionIds,
        ICollection<FormDiagnostic> diagnostics,
        FormElementKind? parentKind,
        int depth,
        ref int elementCount,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        elementCount++;
        var path = $"/layout/{element.Id}";
        if (elementCount > options.MaximumElements)
        {
            diagnostics.Add(Error("PKF030", $"A layout cannot contain more than {options.MaximumElements} elements.", "/layout"));
            return;
        }

        if (depth > options.MaximumLayoutDepth)
        {
            diagnostics.Add(Error("PKF031", $"A layout cannot exceed {options.MaximumLayoutDepth} levels.", path));
            return;
        }

        AddRequired(element.Id, "PKF032", "A layout element identifier is required.", $"{path}/id", diagnostics);
        if (!string.IsNullOrWhiteSpace(element.Id) && !elementIds.Add(element.Id))
        {
            diagnostics.Add(Error("PKF033", $"Layout element identifier '{element.Id}' is duplicated.", $"{path}/id"));
        }

        if (element.Text is not null)
        {
            ValidateText(element.Text, $"{path}/text", diagnostics);
            TrackTranslation(element.Text, translationDefaults, $"{path}/text", diagnostics);
        }

        if (element.Icon is not null)
        {
            AddRequired(element.Icon.Name, "PKF034", "An icon name is required.", $"{path}/icon/name", diagnostics);
        }

        if (element.Visibility is not null)
        {
            if (!fields.ContainsKey(element.Visibility.FieldId))
            {
                diagnostics.Add(Error("PKF035", $"Visibility references unknown field '{element.Visibility.FieldId}'.", $"{path}/visibility/fieldId"));
            }

            var valueRequired = element.Visibility.Operator is FormConditionOperator.Equals or FormConditionOperator.NotEquals;
            if (valueRequired && element.Visibility.Value is null)
            {
                diagnostics.Add(Error("PKF036", "Equality visibility conditions require a comparison value.", $"{path}/visibility/value"));
            }
            else if (!valueRequired && element.Visibility.Value is not null)
            {
                diagnostics.Add(Error("PKF037", "Presence visibility conditions cannot carry a comparison value.", $"{path}/visibility/value"));
            }
        }

        ValidateElementKind(element, fields, placements, actionIds, diagnostics, parentKind, path);
        foreach (var child in element.Elements)
        {
            ValidateElement(
                child,
                fields,
                translationDefaults,
                placements,
                elementIds,
                actionIds,
                diagnostics,
                element.Kind,
                depth + 1,
                ref elementCount,
                cancellationToken);
        }
    }

    /// <summary>Applies invariants specific to controls, wizards, and wizard steps.</summary>
    private static void ValidateElementKind(
        FormElementDefinition element,
        IReadOnlyDictionary<string, FormFieldDefinition> fields,
        IDictionary<string, int> placements,
        IReadOnlySet<string> actionIds,
        ICollection<FormDiagnostic> diagnostics,
        FormElementKind? parentKind,
        string path)
    {
        if (element.Kind == FormElementKind.Control)
        {
            if (string.IsNullOrWhiteSpace(element.FieldId) || !fields.ContainsKey(element.FieldId))
            {
                diagnostics.Add(Error("PKF040", $"A control must reference an existing field; received '{element.FieldId}'.", $"{path}/fieldId"));
            }
            else
            {
                placements.TryGetValue(element.FieldId, out var placementCount);
                placements[element.FieldId] = placementCount + 1;
            }

            if (element.Elements.Count > 0)
            {
                diagnostics.Add(Error("PKF041", "A control cannot contain child elements.", $"{path}/elements"));
            }
        }
        else if (element.FieldId is not null)
        {
            diagnostics.Add(Error("PKF042", "Only a control can reference a field.", $"{path}/fieldId"));
        }

        if (element.Kind == FormElementKind.Wizard)
        {
            if (element.Wizard is null)
            {
                diagnostics.Add(Error("PKF043", "A wizard requires navigation options.", $"{path}/wizard"));
            }

            if (element.Elements.Count == 0 || element.Elements.Any(child => child.Kind != FormElementKind.Step))
            {
                diagnostics.Add(Error("PKF044", "A wizard must contain one or more step elements directly.", $"{path}/elements"));
            }
        }
        else if (element.Wizard is not null)
        {
            diagnostics.Add(Error("PKF045", "Only a wizard can define wizard options.", $"{path}/wizard"));
        }

        if (element.Kind == FormElementKind.Step && parentKind != FormElementKind.Wizard)
        {
            diagnostics.Add(Error("PKF046", "A step must be a direct child of a wizard.", path));
        }

        if (element.Kind == FormElementKind.ActionBar)
        {
            if (element.ActionBar is null)
            {
                diagnostics.Add(Error("PKF047", "An action bar requires ordered action references.", $"{path}/actionBar"));
            }
            else
            {
                if (element.ActionBar.ActionIds.Count == 0)
                {
                    diagnostics.Add(Error("PKF048", "An action bar must reference at least one action.", $"{path}/actionBar/actionIds"));
                }

                var referenced = new HashSet<string>(StringComparer.Ordinal);
                for (var index = 0; index < element.ActionBar.ActionIds.Count; index++)
                {
                    var actionId = element.ActionBar.ActionIds[index];
                    if (!referenced.Add(actionId))
                    {
                        diagnostics.Add(Error("PKF054", $"Action '{actionId}' is repeated in the action bar.", $"{path}/actionBar/actionIds/{index}"));
                    }
                    else if (!actionIds.Contains(actionId))
                    {
                        diagnostics.Add(Error("PKF055", $"Action bar references unknown action '{actionId}'.", $"{path}/actionBar/actionIds/{index}"));
                    }
                }
            }

            if (element.Elements.Count > 0)
            {
                diagnostics.Add(Error("PKF049", "An action bar cannot contain child elements.", $"{path}/elements"));
            }
        }
        else if (element.ActionBar is not null)
        {
            diagnostics.Add(Error("PKF056", "Only an action bar can define action-bar options.", $"{path}/actionBar"));
        }
    }

    /// <summary>Validates stable action identities, handlers, labels, and icon references.</summary>
    private static void ValidateActions(
        IReadOnlyList<FormActionReference> actions,
        IDictionary<string, string> translationDefaults,
        ICollection<FormDiagnostic> diagnostics)
    {
        ArgumentNullException.ThrowIfNull(actions);
        var ids = new HashSet<string>(StringComparer.Ordinal);
        for (var index = 0; index < actions.Count; index++)
        {
            var action = actions[index];
            var path = $"/actions/{index}";
            AddRequired(action.Id, "PKF050", "An action identifier is required.", $"{path}/id", diagnostics);
            if (!string.IsNullOrWhiteSpace(action.Id) && !ids.Add(action.Id))
            {
                diagnostics.Add(Error("PKF051", $"Action identifier '{action.Id}' is duplicated.", $"{path}/id"));
            }

            AddRequired(action.HandlerId, "PKF052", "An action handler identifier is required.", $"{path}/handlerId", diagnostics);
            ValidateText(action.Label, $"{path}/label", diagnostics);
            TrackTranslation(action.Label, translationDefaults, $"{path}/label", diagnostics);
            if (action.Icon is not null)
            {
                AddRequired(action.Icon.Name, "PKF053", "An action icon name is required.", $"{path}/icon/name", diagnostics);
            }
        }
    }

    /// <summary>Reports fields that are missing from or repeated within the visual layout.</summary>
    private static void ValidateFieldPlacement(
        IReadOnlyDictionary<string, FormFieldDefinition> fields,
        IReadOnlyDictionary<string, int> placements,
        ICollection<FormDiagnostic> diagnostics)
    {
        foreach (var field in fields.Values)
        {
            var count = placements.GetValueOrDefault(field.Id);
            if (count == 0)
            {
                diagnostics.Add(new FormDiagnostic("PKF060", FormDiagnosticSeverity.Warning, $"Field '{field.Id}' is not present in the layout.", $"/fields/{field.Id}"));
            }
            else if (count > 1)
            {
                diagnostics.Add(new FormDiagnostic("PKF061", FormDiagnosticSeverity.Warning, $"Field '{field.Id}' is rendered {count} times.", $"/fields/{field.Id}"));
            }
        }
    }

    /// <summary>Requires a stable translation key and a source-language fallback.</summary>
    private static void ValidateText(LocalizedTextReference text, string path, ICollection<FormDiagnostic> diagnostics)
    {
        ArgumentNullException.ThrowIfNull(text);
        AddRequired(text.Key, "PKF070", "A translation key is required.", $"{path}/key", diagnostics);
        AddRequired(text.DefaultText, "PKF071", "Source-language text is required.", $"{path}/defaultText", diagnostics);
    }

    /// <summary>Rejects reuse of a translation key with conflicting source text.</summary>
    private static void TrackTranslation(
        LocalizedTextReference text,
        IDictionary<string, string> translationDefaults,
        string path,
        ICollection<FormDiagnostic> diagnostics)
    {
        if (string.IsNullOrWhiteSpace(text.Key))
        {
            return;
        }

        if (translationDefaults.TryGetValue(text.Key, out var existing) && !string.Equals(existing, text.DefaultText, StringComparison.Ordinal))
        {
            diagnostics.Add(Error("PKF072", $"Translation key '{text.Key}' has conflicting source text.", $"{path}/key"));
        }
        else
        {
            translationDefaults[text.Key] = text.DefaultText;
        }
    }

    /// <summary>Recognizes a bounded interoperable subset of BCP 47 language tags.</summary>
    private static bool IsLocaleTag(string value)
    {
        if (value.Length > 64 || value.StartsWith("-", StringComparison.Ordinal) || value.EndsWith("-", StringComparison.Ordinal))
        {
            return false;
        }

        var segments = value.Split('-');
        return segments.Length > 0
            && segments[0].Length is >= 2 and <= 8
            && segments[0].All(char.IsAsciiLetter)
            && segments.Skip(1).All(segment => segment.Length is >= 1 and <= 8 && segment.All(char.IsAsciiLetterOrDigit));
    }

    /// <summary>Recognizes rooted JSON Pointers with nonempty segments and RFC 6901 escapes.</summary>
    private static bool IsJsonPointer(string value)
    {
        if (string.IsNullOrWhiteSpace(value) || !value.StartsWith("/", StringComparison.Ordinal))
        {
            return false;
        }

        foreach (var segment in value[1..].Split('/'))
        {
            if (segment.Length == 0)
            {
                return false;
            }

            for (var index = 0; index < segment.Length; index++)
            {
                if (segment[index] == '~' && (index + 1 >= segment.Length || segment[++index] is not '0' and not '1'))
                {
                    return false;
                }
            }
        }

        return true;
    }

    /// <summary>Adds a stable required-value diagnostic when an authoring string is blank.</summary>
    private static void AddRequired(
        string value,
        string code,
        string message,
        string path,
        ICollection<FormDiagnostic> diagnostics)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            diagnostics.Add(Error(code, message, path));
        }
    }

    /// <summary>Creates a blocking diagnostic with a stable code and semantic path.</summary>
    private static FormDiagnostic Error(string code, string message, string path) =>
        new(code, FormDiagnosticSeverity.Error, message, path);
}
