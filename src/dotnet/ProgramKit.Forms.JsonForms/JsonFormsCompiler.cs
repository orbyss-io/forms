using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace ProgramKit.Forms;

/// <summary>Compiles Program Kit definitions to bundled JSON Schema and JSON Forms UI Schema.</summary>
public sealed class JsonFormsCompiler : IFormCompiler
{
    /// <summary>Identifies the bundled JSON Schema dialect used for generated data contracts.</summary>
    public const string JsonSchemaDialect = "https://json-schema.org/draft/2020-12/schema";

    /// <summary>Identifies the media type of generated JSON Forms UI Schema artifacts.</summary>
    public const string UiSchemaMediaType = "application/vnd.jsonforms.uischema+json";

    /// <summary>Identifies the default Program Kit wizard renderer contract.</summary>
    public const string WizardRendererId = "ProgramKit.Wizard";

    /// <summary>Identifies the default Program Kit action-bar renderer contract.</summary>
    public const string ActionBarRendererId = "ProgramKit.ActionBar";

    /// <summary>Defines the compatible major version for built-in Program Kit renderers.</summary>
    public const string BuiltInRendererVersionRange = "[1.0.0,2.0.0)";

    /// <summary>Holds the semantic validator applied before target compilation.</summary>
    private readonly IFormDefinitionValidator validator;

    /// <summary>Initializes the compiler with Program Kit's secure default validator.</summary>
    public JsonFormsCompiler()
        : this(new FormDefinitionValidator())
    {
    }

    /// <summary>Initializes the compiler with an application-selected semantic validator.</summary>
    public JsonFormsCompiler(IFormDefinitionValidator validator)
    {
        ArgumentNullException.ThrowIfNull(validator);
        this.validator = validator;
    }

    /// <inheritdoc />
    public async ValueTask<FormCandidate> CompileAsync(
        FormDefinition definition,
        DateTimeOffset compiledAt,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(definition);
        cancellationToken.ThrowIfCancellationRequested();
        var diagnostics = (await validator.ValidateAsync(definition, cancellationToken).ConfigureAwait(false)).ToList();
        var dataSchema = BuildDataSchema(definition, diagnostics, cancellationToken);
        var uiSchema = BuildUiElement(definition.Layout, definition, cancellationToken);
        var dataArtifact = Artifact("application/schema+json", dataSchema);
        var uiArtifact = Artifact(UiSchemaMediaType, uiSchema);
        var renderers = ExtractRenderers(definition).ToArray();
        var translations = ExtractTranslations(definition).ToArray();
        var actions = definition.Actions
            .Select(action => new FormActionRequirement(
                action.Id,
                action.HandlerId,
                action.Kind,
                action.Label,
                action.RequiresValidForm,
                action.Icon))
            .OrderBy(action => action.ActionId, StringComparer.Ordinal)
            .ToArray();
        var candidateHash = Hash(string.Join(
            "\n",
            dataArtifact.Sha256,
            uiArtifact.Sha256,
            ManifestJson(renderers),
            ManifestJson(translations),
            ManifestJson(actions)));

        return new FormCandidate(
            definition.Id,
            definition.Revision,
            dataArtifact,
            uiArtifact,
            renderers,
            translations,
            actions,
            diagnostics,
            compiledAt,
            candidateHash,
            definition.Fields.ToArray());
    }

    /// <summary>Builds a bundled JSON Schema, detecting path collisions that only target mapping can reveal.</summary>
    private static JsonObject BuildDataSchema(
        FormDefinition definition,
        ICollection<FormDiagnostic> diagnostics,
        CancellationToken cancellationToken)
    {
        var root = new JsonObject
        {
            ["$schema"] = JsonSchemaDialect,
            ["$id"] = $"urn:program-kit:forms:{Uri.EscapeDataString(definition.Id.Value)}:{definition.Revision.Value.ToString(CultureInfo.InvariantCulture)}",
            ["title"] = definition.Name,
            ["type"] = "object",
            ["properties"] = new JsonObject(),
            ["additionalProperties"] = false
        };

        foreach (var field in definition.Fields.OrderBy(item => item.DataPath, StringComparer.Ordinal))
        {
            cancellationToken.ThrowIfCancellationRequested();
            AddFieldSchema(root, field, diagnostics);
        }

        return root;
    }

    /// <summary>Adds one field at its JSON Pointer location while preserving intermediate object contracts.</summary>
    private static void AddFieldSchema(
        JsonObject root,
        FormFieldDefinition field,
        ICollection<FormDiagnostic> diagnostics)
    {
        var segments = PointerSegments(field.DataPath);
        if (segments.Count == 0)
        {
            diagnostics.Add(Error("PKFJ001", "A field cannot target the document root.", field.DataPath));
            return;
        }

        var parent = root;
        for (var index = 0; index < segments.Count; index++)
        {
            var properties = EnsureObject(parent, "properties");
            var segment = segments[index];
            var final = index == segments.Count - 1;
            if (final)
            {
                if (properties[segment] is JsonObject existing && existing["type"]?.GetValue<string>() == "object" && field.ValueKind == FormValueKind.Object)
                {
                    MergeFieldSchema(existing, field);
                }
                else if (properties.ContainsKey(segment))
                {
                    diagnostics.Add(Error("PKFJ002", $"Data path '{field.DataPath}' collides with another field.", field.DataPath));
                }
                else
                {
                    properties[segment] = FieldSchema(field);
                }

                if (field.Required)
                {
                    AddRequired(parent, segment);
                }

                return;
            }

            if (properties[segment] is null)
            {
                properties[segment] = new JsonObject
                {
                    ["type"] = "object",
                    ["properties"] = new JsonObject(),
                    ["additionalProperties"] = false
                };
            }

            if (properties[segment] is not JsonObject child || child["type"]?.GetValue<string>() != "object")
            {
                diagnostics.Add(Error("PKFJ003", $"Data path '{field.DataPath}' traverses a non-object field.", field.DataPath));
                return;
            }

            parent = child;
        }
    }

    /// <summary>Creates a JSON Schema fragment for one provider-neutral field.</summary>
    private static JsonObject FieldSchema(FormFieldDefinition field)
    {
        var schema = new JsonObject();
        MergeFieldSchema(schema, field);
        return schema;
    }

    /// <summary>Maps field type, text, constraints, and choices into an existing schema fragment.</summary>
    private static void MergeFieldSchema(JsonObject schema, FormFieldDefinition field)
    {
        schema["type"] = JsonType(field.ValueKind);
        var format = JsonFormat(field.ValueKind);
        if (format is not null)
        {
            schema["format"] = format;
        }
        schema["title"] = field.Label.DefaultText;
        schema["x-i18n"] = field.Label.Key;
        if (field.Description is not null)
        {
            schema["description"] = field.Description.DefaultText;
            schema["x-description-i18n"] = field.Description.Key;
        }

        if (field.ValueKind == FormValueKind.Object)
        {
            schema["properties"] ??= new JsonObject();
            schema["additionalProperties"] ??= false;
        }
        else if (field.ValueKind == FormValueKind.Array)
        {
            schema["items"] = new JsonObject();
        }

        var constraints = field.Constraints;
        if (constraints is null)
        {
            return;
        }

        AddNumber(schema, "minimum", constraints.Minimum);
        AddNumber(schema, "maximum", constraints.Maximum);
        AddNumber(schema, "minLength", constraints.MinimumLength);
        AddNumber(schema, "maxLength", constraints.MaximumLength);
        AddNumber(schema, "minItems", constraints.MinimumItems);
        AddNumber(schema, "maxItems", constraints.MaximumItems);
        if (constraints.Pattern is not null)
        {
            schema["pattern"] = constraints.Pattern;
        }

        if (constraints.Choices is { Count: > 0 } choices)
        {
            schema["oneOf"] = new JsonArray(choices
                .OrderBy(choice => choice.Value, StringComparer.Ordinal)
                .Select(choice => (JsonNode)new JsonObject
                {
                    ["const"] = choice.Value,
                    ["title"] = choice.Label.DefaultText,
                    ["x-i18n"] = choice.Label.Key
                })
                .ToArray());
        }
    }

    /// <summary>Maps a layout node and its children into JSON Forms UI Schema.</summary>
    private static JsonObject BuildUiElement(
        FormElementDefinition element,
        FormDefinition definition,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var result = new JsonObject
        {
            ["type"] = UiType(element.Kind),
            ["id"] = element.Id
        };

        if (element.Kind == FormElementKind.Control && element.FieldId is { } fieldId)
        {
            var field = definition.Fields.FirstOrDefault(item => string.Equals(item.Id, fieldId, StringComparison.Ordinal));
            if (field is not null)
            {
                result["scope"] = SchemaScope(field.DataPath);
                result["label"] = field.Label.DefaultText;
                result["i18n"] = field.Label.Key;
                if (field.Component is not null)
                {
                    var options = EnsureObject(result, "options");
                    options["component"] = field.Component.ComponentId;
                    options["componentVersion"] = field.Component.VersionRange;
                    AddStringMap(options, "componentOptions", field.Component.Options);
                }
            }
        }

        if (element.Text is not null)
        {
            result[element.Kind == FormElementKind.Text ? "text" : "label"] = element.Text.DefaultText;
            result["i18n"] = element.Text.Key;
        }

        var elementOptions = EnsureObject(result, "options");
        AddIcon(elementOptions, element.Icon);
        AddStringMap(elementOptions, "presentation", element.Presentation);
        if (element.Wizard is not null)
        {
            elementOptions["variant"] = "program-kit-wizard";
            elementOptions["navigationPolicy"] = EnumValue(element.Wizard.NavigationPolicy);
            elementOptions["navigationPlacement"] = EnumValue(element.Wizard.NavigationPlacement);
            elementOptions["progressStyle"] = EnumValue(element.Wizard.ProgressStyle);
            elementOptions["validateBeforeAdvance"] = element.Wizard.ValidateBeforeAdvance;
            elementOptions["saveProgress"] = element.Wizard.SaveProgress;
            elementOptions["deepLink"] = element.Wizard.DeepLink;
        }

        if (element.ActionBar is not null)
        {
            elementOptions["actions"] = new JsonArray(element.ActionBar.ActionIds
                .Select(actionId => (JsonNode)actionId)
                .ToArray());
        }

        if (element.Visibility is not null)
        {
            result["rule"] = BuildRule(element.Visibility, definition);
        }

        if (element.Elements.Count > 0)
        {
            result["elements"] = new JsonArray(element.Elements
                .Select(child => (JsonNode)BuildUiElement(child, definition, cancellationToken))
                .ToArray());
        }

        if (elementOptions.Count == 0)
        {
            result.Remove("options");
        }

        return result;
    }

    /// <summary>Compiles a bounded visibility comparison to a JSON Forms SHOW rule.</summary>
    private static JsonObject BuildRule(FormVisibilityCondition visibility, FormDefinition definition)
    {
        var field = definition.Fields.FirstOrDefault(item => string.Equals(item.Id, visibility.FieldId, StringComparison.Ordinal));
        var condition = new JsonObject { ["scope"] = field is null ? "#" : SchemaScope(field.DataPath) };
        condition["schema"] = visibility.Operator switch
        {
            FormConditionOperator.Equals => new JsonObject { ["const"] = visibility.Value },
            FormConditionOperator.NotEquals => new JsonObject { ["not"] = new JsonObject { ["const"] = visibility.Value } },
            FormConditionOperator.IsPresent => new JsonObject { ["not"] = new JsonObject { ["type"] = "null" } },
            FormConditionOperator.IsAbsent => new JsonObject { ["type"] = "null" },
            _ => new JsonObject()
        };
        return new JsonObject { ["effect"] = "SHOW", ["condition"] = condition };
    }

    /// <summary>Extracts and deterministically orders installed and built-in renderer requirements.</summary>
    private static IEnumerable<FormRendererRequirement> ExtractRenderers(FormDefinition definition)
    {
        var renderers = definition.Fields
            .Where(field => field.Component is not null)
            .Select(field => new FormRendererRequirement(field.Component!.ComponentId, field.Component.VersionRange))
            .ToList();
        Walk(definition.Layout, element =>
        {
            if (element.Kind == FormElementKind.Wizard)
            {
                renderers.Add(new FormRendererRequirement(WizardRendererId, BuiltInRendererVersionRange));
            }
            else if (element.Kind == FormElementKind.ActionBar)
            {
                renderers.Add(new FormRendererRequirement(ActionBarRendererId, BuiltInRendererVersionRange));
            }
        });
        return renderers
            .DistinctBy(renderer => (renderer.ComponentId, renderer.VersionRange))
            .OrderBy(renderer => renderer.ComponentId, StringComparer.Ordinal)
            .ThenBy(renderer => renderer.VersionRange, StringComparer.Ordinal);
    }

    /// <summary>Extracts stable source-language requirements without making Forms own translation values.</summary>
    private static IEnumerable<FormTranslationRequirement> ExtractTranslations(FormDefinition definition)
    {
        var requirements = new Dictionary<string, FormTranslationRequirement>(StringComparer.Ordinal);
        var scope = $"forms:{definition.Id.Value}";
        foreach (var field in definition.Fields)
        {
            AddTranslation(requirements, field.Label, definition.SourceLocale, scope);
            if (field.Description is not null)
            {
                AddTranslation(requirements, field.Description, definition.SourceLocale, scope);
            }

            if (field.Constraints?.Choices is { } choices)
            {
                foreach (var choice in choices)
                {
                    AddTranslation(requirements, choice.Label, definition.SourceLocale, scope);
                }
            }
        }

        Walk(definition.Layout, element =>
        {
            if (element.Text is not null)
            {
                AddTranslation(requirements, element.Text, definition.SourceLocale, scope);
            }
        });
        foreach (var action in definition.Actions)
        {
            AddTranslation(requirements, action.Label, definition.SourceLocale, scope);
        }

        return requirements.Values.OrderBy(requirement => requirement.Key, StringComparer.Ordinal);
    }

    /// <summary>Adds one translation requirement, relying on semantic validation for conflicts.</summary>
    private static void AddTranslation(
        IDictionary<string, FormTranslationRequirement> requirements,
        LocalizedTextReference text,
        string sourceLocale,
        string scope)
    {
        requirements.TryAdd(text.Key, new FormTranslationRequirement(text.Key, text.DefaultText, sourceLocale, scope, text.Context));
    }

    /// <summary>Visits every element in document order without exposing a mutable layout abstraction.</summary>
    private static void Walk(FormElementDefinition element, Action<FormElementDefinition> visit)
    {
        visit(element);
        foreach (var child in element.Elements)
        {
            Walk(child, visit);
        }
    }

    /// <summary>Creates a canonical artifact using stable indentation and a SHA-256 content digest.</summary>
    private static FormArtifact Artifact(string mediaType, JsonNode content)
    {
        // System.Text.Json follows the host newline for indented output. Artifacts are hashed and
        // exchanged across operating systems, so preserve one explicit canonical representation.
        var json = content.ToJsonString(new JsonSerializerOptions { WriteIndented = true })
            .ReplaceLineEndings("\r\n");
        return new FormArtifact(mediaType, json, Hash(json));
    }

    /// <summary>Serializes an already deterministically ordered manifest for candidate hashing.</summary>
    private static string ManifestJson<T>(IReadOnlyList<T> values) => JsonSerializer.Serialize(values);

    /// <summary>Computes a lowercase hexadecimal SHA-256 digest over UTF-8 content.</summary>
    private static string Hash(string content) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(content)));

    /// <summary>Maps provider-neutral value kinds to JSON Schema primitive types and formats.</summary>
    private static string JsonType(FormValueKind kind) => kind switch
    {
        FormValueKind.String or FormValueKind.Date or FormValueKind.DateTime or FormValueKind.Time => "string",
        FormValueKind.Integer => "integer",
        FormValueKind.Number => "number",
        FormValueKind.Boolean => "boolean",
        FormValueKind.Object => "object",
        FormValueKind.Array => "array",
        _ => "string"
    };

    /// <summary>Maps temporal value kinds to JSON Schema format annotations.</summary>
    private static string? JsonFormat(FormValueKind kind) => kind switch
    {
        FormValueKind.Date => "date",
        FormValueKind.DateTime => "date-time",
        FormValueKind.Time => "time",
        _ => null
    };

    /// <summary>Maps provider-neutral layout kinds to JSON Forms or Program Kit extension types.</summary>
    private static string UiType(FormElementKind kind) => kind switch
    {
        FormElementKind.Control => "Control",
        FormElementKind.Group => "Group",
        FormElementKind.HorizontalLayout => "HorizontalLayout",
        FormElementKind.VerticalLayout => "VerticalLayout",
        FormElementKind.Wizard => "Categorization",
        FormElementKind.Step => "Category",
        FormElementKind.Text => "Label",
        FormElementKind.ActionBar => ActionBarRendererId,
        _ => "VerticalLayout"
    };

    /// <summary>Transforms an enum name into stable lower camel case JSON text.</summary>
    private static string EnumValue<T>(T value)
        where T : struct, Enum
    {
        var name = value.ToString();
        return char.ToLowerInvariant(name[0]) + name[1..];
    }

    /// <summary>Transforms a form JSON Pointer into a JSON Schema scope understood by JSON Forms.</summary>
    private static string SchemaScope(string dataPath) =>
        "#" + string.Concat(PointerSegments(dataPath).Select(segment => "/properties/" + EscapePointer(segment)));

    /// <summary>Parses and unescapes a rooted JSON Pointer into property-name segments.</summary>
    private static IReadOnlyList<string> PointerSegments(string pointer)
    {
        if (string.IsNullOrEmpty(pointer) || !pointer.StartsWith("/", StringComparison.Ordinal))
        {
            return [];
        }

        return pointer[1..]
            .Split('/')
            .Select(segment => segment.Replace("~1", "/", StringComparison.Ordinal).Replace("~0", "~", StringComparison.Ordinal))
            .ToArray();
    }

    /// <summary>Escapes a property name for safe use inside a JSON Pointer.</summary>
    private static string EscapePointer(string segment) =>
        segment.Replace("~", "~0", StringComparison.Ordinal).Replace("/", "~1", StringComparison.Ordinal);

    /// <summary>Gets or creates a child object at the supplied property.</summary>
    private static JsonObject EnsureObject(JsonObject parent, string property)
    {
        if (parent[property] is JsonObject existing)
        {
            return existing;
        }

        var created = new JsonObject();
        parent[property] = created;
        return created;
    }

    /// <summary>Adds a field name to an object's unique required-property array.</summary>
    private static void AddRequired(JsonObject parent, string property)
    {
        if (parent["required"] is not JsonArray required)
        {
            required = [];
            parent["required"] = required;
        }

        if (!required.Any(item => string.Equals(item?.GetValue<string>(), property, StringComparison.Ordinal)))
        {
            required.Add(property);
        }
    }

    /// <summary>Adds a nullable numeric constraint using invariant JSON number semantics.</summary>
    private static void AddNumber<T>(JsonObject parent, string property, T? value)
        where T : struct
    {
        if (value.HasValue)
        {
            parent[property] = JsonValue.Create(value.Value);
        }
    }

    /// <summary>Adds an allowlisted string map in deterministic key order.</summary>
    private static void AddStringMap(JsonObject parent, string property, IReadOnlyDictionary<string, string>? values)
    {
        if (values is null || values.Count == 0)
        {
            return;
        }

        parent[property] = new JsonObject(values
            .OrderBy(item => item.Key, StringComparer.Ordinal)
            .Select(item => KeyValuePair.Create<string, JsonNode?>(item.Key, item.Value)));
    }

    /// <summary>Adds a validated icon reference to renderer options.</summary>
    private static void AddIcon(JsonObject options, FormIconReference? icon)
    {
        if (icon is null)
        {
            return;
        }

        options["icon"] = new JsonObject { ["name"] = icon.Name, ["bundle"] = icon.Bundle };
    }

    /// <summary>Creates a target-specific blocking compiler diagnostic.</summary>
    private static FormDiagnostic Error(string code, string message, string path) =>
        new(code, FormDiagnosticSeverity.Error, message, path);
}
