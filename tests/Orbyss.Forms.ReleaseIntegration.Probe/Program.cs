using System.Text.Json;
using Orbyss.Forms;

var json = new JsonSerializerOptions(JsonSerializerDefaults.Web) { WriteIndented = true };
var custom = new FormCondition("kind", FormConditionOperator.Equals, JsonSerializer.SerializeToElement("custom"));
var editable = new FormCondition("editable", FormConditionOperator.Equals, JsonSerializer.SerializeToElement(true));
var fields = new FormFieldDefinition[]
{
    new("name", "/name", FormValueKind.String, true, Text("fields.name", "Name"), Description: Text("fields.name.help", "Use a fictitious name for this example."), Constraints: new(MinimumLength: 1)),
    new("kind", "/kind", FormValueKind.String, true, Text("fields.kind", "Product type"), Constraints: new(Choices: [new("standard", Text("choices.standard", "Standard")), new("custom", Text("choices.custom", "Custom"))])),
    new("editable", "/editable", FormValueKind.Boolean, false, Text("fields.editable", "Allow editing")),
    new("detail", "/detail", FormValueKind.String, false, Text("fields.detail", "Custom detail"), Constraints: new(MinimumLength: 1), RequiredWhen: custom),
    new("quantity", "/quantity", FormValueKind.Integer, true, Text("fields.quantity", "Quantity"), Constraints: new(Minimum: 1, Maximum: 100)),
    new("reference", "/reference", FormValueKind.String, false, Text("fields.reference", "Reference"), ReadOnly: true)
};
var definition = new FormDefinition(new("synthetic-product"), new(1), "Synthetic configurable product", "en", FormLifecycleState.Draft, fields,
    new("journey", FormElementKind.Wizard,
    [
        new("configure", FormElementKind.Step,
        [
            Control("name"), Control("kind"), Control("editable"),
            new("editable-details", FormElementKind.VerticalLayout,
                [Control("detail") with { VisibleWhen = custom, EnabledWhen = custom }], EnabledWhen: editable)
        ], Text: Text("steps.configure", "Configure")),
        new("review", FormElementKind.Step,
        [
            Control("quantity"), Control("reference") with { EnabledWhen = editable },
            new("actions", FormElementKind.ActionBar, [], ActionBar: new(["calculate"]))
        ], Text: Text("steps.review", "Review"))
    ], Wizard: new(FormWizardNavigationPolicy.Visited, FormWizardNavigationPlacement.Adaptive, FormWizardProgressStyle.Progress, ValidateBeforeAdvance: false)),
    [new("calculate", FormActionKind.Custom, Text("actions.calculate", "Calculate"), "synthetic.calculate", true)]);
var compiler = new JsonFormsCompiler();
var releases = new InMemoryFormReleaseStore();
var catalog = new DefaultFormCatalogService(new InMemoryFormDefinitionStore(), releases, releases, new FormDefinitionValidator(), compiler);
var created = await catalog.CreateAsync(definition, Mutation("create", null, "author", 1));
var review = await catalog.SubmitForReviewAsync(definition.Id, definition.Revision, ["synthetic:public-api-producer"], Mutation("review", created.Version, "author", 2));
var approved = await catalog.ApproveAsync(definition.Id, definition.Revision, Mutation("approve", review.Version, "reviewer", 3));
var published = await catalog.PublishAsync(definition.Id, definition.Revision, Mutation("publish", approved.Version, "publisher", 4));
var release = published.Value;
Require(release.Id.Value == "synthetic-product-v1" && !release.Retired, "Catalog did not publish the expected immutable release.");
var replay = await catalog.PublishAsync(definition.Id, definition.Revision, Mutation("publish", approved.Version, "publisher", 4));
Require(replay.WasReplay && JsonSerializer.Serialize(replay.Value, json) == JsonSerializer.Serialize(release, json), "Publication replay drifted.");

var cases = new List<object>();
var dataValidator = new DefaultFormDataValidator();
foreach (var quantity in new[] { "1e30", "-1e30", "100.0001" })
{
    var diagnostics = await dataValidator.ValidateAsync(release, new FormDataDocument("{\"name\":\"Ada\",\"kind\":\"standard\",\"quantity\":" + quantity + "}", "test"), FormDataValidationMode.Submission);
    Require(diagnostics.Any(d => d.DataPath == "/quantity"), "Numeric bounds were bypassed outside decimal range.");
}
foreach (var (kind, expected) in new[] { (FormValueKind.String, "\"yes\""), (FormValueKind.Boolean, "true"), (FormValueKind.Number, "2.5"), (FormValueKind.Integer, "2") })
foreach (var operation in Enum.GetValues<FormConditionOperator>())
{
    var condition = new FormCondition("source", operation, operation is FormConditionOperator.Equals or FormConditionOperator.NotEquals ? JsonDocument.Parse(expected).RootElement.Clone() : null);
    var source = new FormFieldDefinition("source", "/nested/source", kind, false, Text("source", "Source"));
    var target = new FormFieldDefinition("target", "/answer/value", FormValueKind.String, false, Text("target", "Target"), Constraints: new(MinimumLength: 1), RequiredWhen: condition);
    var caseDefinition = definition with { Fields = [source, target], Layout = new("root", FormElementKind.VerticalLayout, [Control("source"), Control("target")]), Actions = [] };
    var candidate = await compiler.CompileAsync(caseDefinition, DateTimeOffset.UnixEpoch);
    Require(candidate.Diagnostics.All(d => d.Severity != FormDiagnosticSeverity.Error), "Valid typed condition failed authoring.");
    var caseRelease = release with { Candidate = candidate };
    var vectors = new List<object>();
    foreach (var discriminator in new[] { "missing", "null", expected, "\"other\"", "false", "0", "\"\"", "{}", "[]" })
    foreach (var answer in new[] { "missing", "\"ok\"", "\"\"", "null" })
    {
        var input = "{" + (discriminator == "missing" ? "" : "\"nested\":{\"source\":" + discriminator + "},")
            + (answer == "missing" ? "" : "\"answer\":{\"value\":" + answer + "},") + "\"unused\":true}";
        // No extraneous data: the server field validator and JSON Schema have independent unknown-field policies.
        input = input.Replace(",\"unused\":true", "", StringComparison.Ordinal).Replace("\"unused\":true", "", StringComparison.Ordinal);
        var document = new FormDataDocument(input, "test");
        var diagnostics = await dataValidator.ValidateAsync(caseRelease, document, FormDataValidationMode.Submission);
        var draft = await dataValidator.ValidateAsync(caseRelease, document, FormDataValidationMode.Draft);
        using var parsed = JsonDocument.Parse(input);
        var triggered = condition.Evaluate(parsed.RootElement, caseDefinition.Fields);
        Require(diagnostics.Any(d => d.Code == "PKFD001") == (triggered && answer == "missing"), "Conditional requiredness is not explicit.");
        Require(draft.All(d => d.Code != "PKFD001"), "Draft validation required an absent value.");
        vectors.Add(new { data = parsed.RootElement.Clone(), valid = diagnostics.Count == 0, draftValid = draft.Count == 0 });
    }
    foreach (var input in new[] { "[]", "null", "{\"nested\":null,\"answer\":{\"value\":\"ok\"}}", "{\"nested\":[]}", "{\"answer\":null}", "{\"answer\":\"wrong\"}", "{\"nested\":{},\"answer\":{}}", "{\"nested\":{\"source\":2.0},\"answer\":{\"value\":\"ok\"}}" })
    {
        var document = new FormDataDocument(input, "test");
        var diagnostics = await dataValidator.ValidateAsync(caseRelease, document, FormDataValidationMode.Submission);
        var draft = await dataValidator.ValidateAsync(caseRelease, document, FormDataValidationMode.Draft);
        vectors.Add(new { data = JsonDocument.Parse(input).RootElement.Clone(), valid = diagnostics.Count == 0, draftValid = draft.Count == 0 });
    }
    cases.Add(new { name = $"{kind}-{operation}", schema = JsonDocument.Parse(candidate.DataSchema.Content).RootElement.Clone(), vectors });
    var without = await compiler.CompileAsync(caseDefinition with { Fields = [source, target with { RequiredWhen = null }] }, DateTimeOffset.UnixEpoch);
    var compatibility = await new DefaultFormCompatibilityAnalyzer().AnalyzeAsync(release with { Candidate = without }, candidate);
    Require(compatibility.RequiresMigration, "A newly conditional required field was not classified as breaking.");
}
var invalid = definition with { Fields = fields.Select(f => f.Id == "detail" ? f with { Required = true } : f).ToArray() };
Require((await new FormDefinitionValidator().ValidateAsync(invalid)).Any(d => d.Code == "PKF080"), "Conflicting requiredness was accepted.");
foreach (var condition in new[] { new FormCondition("unknown", FormConditionOperator.IsPresent), new FormCondition("kind", FormConditionOperator.Equals, JsonSerializer.SerializeToElement(1)), new FormCondition("kind", FormConditionOperator.IsAbsent, JsonSerializer.SerializeToElement("unexpected")) })
{
    var malformed = definition with { Fields = fields.Select(f => f.Id == "detail" ? f with { RequiredWhen = condition } : f).ToArray() };
    Require((await new FormDefinitionValidator().ValidateAsync(malformed)).Any(d => d.Code is "PKF082" or "PKF083"), "Invalid typed condition was accepted.");
}
var legacy = await compiler.CompileAsync(definition with { Layout = definition.Layout with { VisibleWhen = null, Visibility = new("kind", FormConditionOperator.Equals, "standard") } }, DateTimeOffset.UnixEpoch);
Require(legacy.UiSchema.Content.Contains("SHOW", StringComparison.Ordinal), "Legacy visibility no longer compiles.");

var releaseJson = JsonSerializer.Serialize(release, json).Replace("\r\n", "\n", StringComparison.Ordinal);
var output = JsonSerializer.Serialize(new { release, releaseJson, cases }, json).Replace("\r\n", "\n", StringComparison.Ordinal) + "\n";
if (args.Length == 2 && args[0] == "--output") await File.WriteAllTextAsync(args[1], output);
else if (args.Length == 1 && args[0] == "--print") Console.Write(output);
else Console.WriteLine($"Published release integration and {cases.Count} condition parity groups passed.");

static LocalizedTextReference Text(string key, string fallback) => new(key, fallback);
static FormElementDefinition Control(string field) => new(field + "-control", FormElementKind.Control, [], FieldId: field);
static FormMutationContext Mutation(string key, FormConcurrencyToken? version, string actor, int day) => new(key, version, new(actor, "synthetic"), DateTimeOffset.UnixEpoch.AddDays(day), "release-integration");
static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
