using System.Text.Json;
using Orbyss.Forms;
using Orbyss.Forms.Localization;
using Orbyss.Localization;

var actor = new FormAuditActor("author-1", "user", "Form Author");
var mutation = new FormMutationContext(
    "create-registration-v1",
    new FormConcurrencyToken("draft-7"),
    actor,
    DateTimeOffset.UnixEpoch,
    "correlation-1");
var name = new FormFieldDefinition(
    "name",
    "/name",
    FormValueKind.String,
    true,
    new LocalizedTextReference("name", "Name"),
    Constraints: new FormConstraints(MinimumLength: 1, MaximumLength: 200));
var step = new FormElementDefinition(
    "identity",
    FormElementKind.Step,
    [
        new FormElementDefinition("name-control", FormElementKind.Control, [], FieldId: "name"),
        new FormElementDefinition(
            "actions",
            FormElementKind.ActionBar,
            [],
            ActionBar: new FormActionBarOptions(["finish"]))
    ],
    Text: new LocalizedTextReference("steps.identity", "Identity"),
    Icon: new FormIconReference("user"));
var wizard = new FormElementDefinition(
    "registration",
    FormElementKind.Wizard,
    [step],
    Wizard: new FormWizardOptions(
        FormWizardNavigationPolicy.Visited,
        FormWizardNavigationPlacement.Adaptive,
        FormWizardProgressStyle.Progress,
        SaveProgress: true));
var definition = new FormDefinition(
    new FormId("registration"),
    new FormRevision(7),
    "Registration",
    "en",
    FormLifecycleState.Draft,
    [name],
    wizard,
    [new FormActionReference("finish", FormActionKind.Submit, new LocalizedTextReference("actions.finish", "Finish"), "registration.submit", true)]);

Require(mutation.ExpectedVersion?.Value == "draft-7", "form concurrency token lost");
Require(definition.Layout.Wizard?.SaveProgress == true, "wizard persistence policy lost");
Require(definition.Layout.Elements.Single().Icon?.Name == "user", "step icon lost");
var validator = new FormDefinitionValidator();
var validDiagnostics = await validator.ValidateAsync(definition);
Require(validDiagnostics.All(item => item.Severity != FormDiagnosticSeverity.Error), "valid form was rejected");
var invalidDefinition = definition with
{
    Layout = new FormElementDefinition("broken", FormElementKind.Control, [], FieldId: "missing")
};
var invalidDiagnostics = await validator.ValidateAsync(invalidDefinition);
Require(invalidDiagnostics.Any(item => item.Code == "PKF040"), "unknown field reference was accepted");
var malformedFieldDefinition = definition with
{
    Fields =
    [
        name with { DataPath = "/bad~2path" },
        name with
        {
            Id = "amount",
            DataPath = "/amount",
            ValueKind = FormValueKind.Number,
            Label = new LocalizedTextReference("name", "Different text"),
            Constraints = new FormConstraints(MinimumLength: 2)
        }
    ]
};
var malformedFieldDiagnostics = await validator.ValidateAsync(malformedFieldDefinition);
Require(malformedFieldDiagnostics.Any(item => item.Code == "PKF013"), "malformed JSON Pointer was accepted");
Require(malformedFieldDiagnostics.Any(item => item.Code == "PKF029"), "type-inapplicable constraint was accepted");
Require(malformedFieldDiagnostics.Any(item => item.Code == "PKF072"), "conflicting field translation defaults were accepted");
var compatibility = new FormCompatibilityReport(
    new FormReleaseId("registration-v1"),
    definition.Revision,
    [new FormCompatibilityIssue("PKF100", FormCompatibilityImpact.Breaking, "Required field added", "/name")]);
Require(compatibility.RequiresMigration, "breaking form change did not require migration");
var baselineField = name with { Required = false, Constraints = new FormConstraints(MaximumLength: 200) };
var candidateField = name with { Required = true, Constraints = new FormConstraints(MaximumLength: 100) };
var baselineCandidate = Candidate(definition, baselineField, "baseline");
var nextCandidate = Candidate(definition with { Revision = new FormRevision(8) }, candidateField, "next");
var analyzer = new DefaultFormCompatibilityAnalyzer();
var baselineRelease = new FormRelease(new FormReleaseId("registration-v1"), baselineCandidate, DateTimeOffset.UnixEpoch, actor, []);
var analyzedCompatibility = await analyzer.AnalyzeAsync(
    baselineRelease,
    nextCandidate);
Require(analyzedCompatibility.RequiresMigration, "stricter required field was not classified as breaking");
Require(analyzedCompatibility.Issues.Any(item => item.Code == "PKFC104"), "required-field compatibility finding missing");
var compiler = new JsonFormsCompiler(validator);
var compiled = await compiler.CompileAsync(definition, DateTimeOffset.UnixEpoch);
Require(compiled.Diagnostics.All(item => item.Severity != FormDiagnosticSeverity.Error), "valid definition did not compile");
Require(compiled.DataSchema.Content.Contains("\"$schema\"", StringComparison.Ordinal), "JSON Schema dialect missing");
Require(compiled.UiSchema.Content.Contains("orbyss-forms-wizard", StringComparison.Ordinal), "wizard rendering contract missing");
Require(compiled.Renderers.Any(item => item.ComponentId == JsonFormsCompiler.WizardRendererId), "consumer-supplied wizard renderer requirement missing");
Require(compiled.Renderers.Any(item => item.ComponentId == JsonFormsCompiler.ActionBarRendererId), "consumer-supplied action-bar renderer requirement missing");
Require(compiled.Translations.Any(item => item.Key == "steps.identity" && item.Scope == "forms:registration"), "scoped translation requirement missing");
Require(compiled.Actions.Single().HandlerId == "registration.submit", "action manifest missing");
Require(compiled.Actions.Single().Label.Key == "actions.finish" && compiled.Actions.Single().RequiresValidForm, "action presentation policy missing");
using (var compiledUi = JsonDocument.Parse(compiled.UiSchema.Content))
{
    var actionReferences = compiledUi.RootElement
        .GetProperty("elements")[0]
        .GetProperty("elements")[1]
        .GetProperty("options")
        .GetProperty("actions");
    Require(
        actionReferences.GetArrayLength() == 1 && actionReferences[0].GetString() == "finish",
        "action-bar references missing");
}
Require(compiled.CandidateSha256.Length == 64 && compiled.DataSchema.Sha256.Length == 64, "artifact hashes missing");
Require(
    !compiled.DataSchema.Content.Replace("\r\n", string.Empty, StringComparison.Ordinal).Contains('\n')
    && !compiled.UiSchema.Content.Replace("\r\n", string.Empty, StringComparison.Ordinal).Contains('\n'),
    "compiled artifacts contain platform-dependent newlines");
if (args.Contains("--print-frontend-fixture", StringComparer.Ordinal))
{
    var releaseFixture = new FormRelease(
        new FormReleaseId("registration-v7"),
        compiled,
        DateTimeOffset.UnixEpoch,
        actor,
        ["compiler-contract"]);
    Console.Write(JsonSerializer.Serialize(releaseFixture, new JsonSerializerOptions(JsonSerializerDefaults.Web)
    {
        WriteIndented = true
    }));
    return;
}
var replayed = await compiler.CompileAsync(definition, DateTimeOffset.UnixEpoch);
Require(replayed.CandidateSha256 == compiled.CandidateSha256, "identical compilation was not deterministic");
var unknownActionDefinition = definition with
{
    Layout = wizard with
    {
        Elements =
        [
            step with
            {
                Elements =
                [
                    new FormElementDefinition("name-control", FormElementKind.Control, [], FieldId: "name"),
                    new FormElementDefinition("unknown-actions", FormElementKind.ActionBar, [], ActionBar: new FormActionBarOptions(["missing"]))
                ]
            }
        ]
    }
};
var unknownActionDiagnostics = await validator.ValidateAsync(unknownActionDefinition);
Require(unknownActionDiagnostics.Any(item => item.Code == "PKF055"), "unknown action-bar reference was accepted");
var collisionDefinition = definition with
{
    Fields =
    [
        name with { Id = "customer", DataPath = "/customer" },
        name with { Id = "customer-name", DataPath = "/customer/name" }
    ]
};
var collisionCandidate = await compiler.CompileAsync(collisionDefinition, DateTimeOffset.UnixEpoch);
Require(collisionCandidate.Diagnostics.Any(item => item.Code == "PKFJ003"), "non-object data-path traversal was accepted");
var formsStorePath = Path.Combine(Path.GetTempPath(), "forms-store-" + Guid.NewGuid().ToString("N"));
try
{
    var formsStore = new FileSystemFormReleaseStore(new FileSystemFormReleaseStoreOptions(formsStorePath));
    await formsStore.WriteAsync(baselineRelease);
    await formsStore.WriteAsync(baselineRelease);
    var storedFormRelease = await formsStore.GetAsync(baselineRelease.Id);
    Require(storedFormRelease?.Candidate.FormId == definition.Id, "form release filesystem roundtrip failed");
    var formReleaseCount = 0;
    await foreach (var _ in formsStore.FindByFormAsync(definition.Id))
    {
        formReleaseCount++;
    }

    Require(formReleaseCount == 1, "idempotent form release replay created a duplicate");
    var formOverwriteRejected = false;
    try
    {
        await formsStore.WriteAsync(baselineRelease with { Retired = true });
    }
    catch (InvalidOperationException)
    {
        formOverwriteRejected = true;
    }

    Require(formOverwriteRejected, "immutable form release overwrite was accepted");
}
finally
{
    if (Directory.Exists(formsStorePath))
    {
        Directory.Delete(formsStorePath, recursive: true);
    }
}


var formScope = new LocalizationScope(LocalizationScopeKind.Form, "registration");
var message = new LocalizationMessageDefinition(
    "steps.identity",
    formScope,
    "Identity",
    [],
    [new LocalizedValue("nl", "Identiteit", LocalizationValueState.Reviewed, "human")]);
var catalog = new LocalizationCatalogDefinition(
    new LocalizationCatalogId("application"),
    new LocalizationRevision(3),
    "Application",
    "en",
    LocalizationLifecycleState.Draft,
    [new LocaleDefinition("en", TextDirection.LeftToRight, RequiredForPublication: true), new LocaleDefinition("nl", TextDirection.LeftToRight, "en")],
    [message]);
var bridge = new DefaultFormLocalizationBridge();
var merge = bridge.Merge(compiled, catalog);
Require(merge.Succeeded && merge.AddedMessages == 2 && merge.RetainedMessages == 1, "form translation manifest merge failed");
Require(merge.Catalog.Revision.Value == catalog.Revision.Value + 1, "successful translation merge did not advance revision");
Require(merge.Catalog.Messages.Single(item => item.Key == "steps.identity").Values.Single().Pattern == "Identiteit", "translation merge replaced human values");
var conflictingCatalog = catalog with
{
    Messages = [message with { SourcePattern = "Conflicting source" }]
};
var conflictingMerge = bridge.Merge(compiled, conflictingCatalog);
Require(!conflictingMerge.Succeeded && conflictingMerge.Diagnostics.Any(item => item.Code == "PKFL003"), "conflicting form translation source was accepted");
Require(conflictingMerge.Catalog.Revision == conflictingCatalog.Revision, "failed translation merge advanced revision");
Require(typeof(IFormAuthoring).Assembly.GetReferencedAssemblies().All(IsAllowedDependency), "forms contract leaked an implementation dependency");

Console.WriteLine("Orbyss Forms contract and Localization bridge probe passed.");

static FormCandidate Candidate(FormDefinition definition, FormFieldDefinition field, string hash)
{
    var artifact = new FormArtifact("application/schema+json", "{}", hash);
    return new FormCandidate(
        definition.Id,
        definition.Revision,
        artifact,
        artifact,
        [],
        [],
        [],
        [],
        DateTimeOffset.UnixEpoch,
        hash,
        [field]);
}

static bool IsAllowedDependency(System.Reflection.AssemblyName dependency) =>
    dependency.Name is not { } name
    || (!name.Contains("AspNetCore", StringComparison.Ordinal)
        && !name.Contains("EntityFrameworkCore", StringComparison.Ordinal)
        && !name.Contains("JsonForms", StringComparison.OrdinalIgnoreCase)
        && !name.Contains("CodeMirror", StringComparison.OrdinalIgnoreCase)
        && !name.Contains("Monaco", StringComparison.OrdinalIgnoreCase));

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
