using System.Text;
using System.Text.Json;
using System.IO.Compression;
using ProgramKit.Forms;
using ProgramKit.Forms.Localization;
using ProgramKit.Localization;
using ProgramKit.Localization.Formats;

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
Require(compiled.UiSchema.Content.Contains("program-kit-wizard", StringComparison.Ordinal), "wizard rendering contract missing");
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
var formsStorePath = Path.Combine(Path.GetTempPath(), "program-kit-forms-store-" + Guid.NewGuid().ToString("N"));
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

var localizationActor = new LocalizationAuditActor("translator-1", "user", "Translator");
var localizationMutation = new LocalizationMutationContext(
    "import-registration-nl",
    new LocalizationConcurrencyToken("catalog-3"),
    localizationActor,
    DateTimeOffset.UnixEpoch);
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
var import = new LocalizationImportRequest(
    LocalizationImportFormat.Csv,
    Encoding.UTF8.GetBytes("key,nl\nsteps.identity,Identiteit"),
    LocalizationMergePolicy.PreserveExisting,
    formScope,
    new Dictionary<string, string> { ["key"] = "key", ["nl"] = "nl" },
    "registration.csv");

Require(localizationMutation.ExpectedVersion?.Value == "catalog-3", "localization concurrency token lost");
Require(catalog.Messages.Single().Scope == formScope, "structured form scope lost");
Require(import.Content.Length > 0 && import.Format == LocalizationImportFormat.Csv, "bounded import content lost");
var formatOptions = new LocalizationImportFormatOptions(MaximumContentBytes: 1_000_000, MaximumExpandedBytes: 2_000_000, MaximumRows: 100);
var csvAdapter = new CsvLocalizationImportAdapter(formatOptions);
var csvRequest = new LocalizationImportRequest(
    LocalizationImportFormat.Csv,
    Encoding.UTF8.GetBytes("key,source,nl\nsteps.identity,Identity,Identiteit\nfields.email,Email,E-mailadres"),
    LocalizationMergePolicy.PreserveExisting,
    formScope,
    new Dictionary<string, string> { ["key"] = "key", ["source"] = "source", ["nl"] = "nl" },
    "registration.csv");
var csvDocument = await csvAdapter.ParseAsync(csvRequest);
Require(csvDocument.Entries.Count == 2 && csvDocument.Entries[1].SourcePattern == "Email", "wide CSV import mapping failed");
var jsonAdapter = new JsonLocalizationImportAdapter(formatOptions);
var jsonDocument = await jsonAdapter.ParseAsync(new LocalizationImportRequest(
    LocalizationImportFormat.Json,
    Encoding.UTF8.GetBytes("""{"entries":[{"key":"fields.name","languageTag":"nl","pattern":"Naam","sourcePattern":"Name","scope":{"kind":"Form","resourceId":"registration"}}]}"""),
    LocalizationMergePolicy.ReplaceImported,
    SourceName: "registration.json"));
Require(jsonDocument.Entries.Single().Scope == formScope, "JSON structured scope import failed");
var poAdapter = new PoLocalizationImportAdapter(formatOptions);
var poDocument = await poAdapter.ParseAsync(new LocalizationImportRequest(
    LocalizationImportFormat.Po,
    Encoding.UTF8.GetBytes("msgctxt \"fields.name\"\nmsgid \"Name\"\nmsgstr \"Naam\"\n"),
    LocalizationMergePolicy.ReplaceImported,
    formScope,
    new Dictionary<string, string> { ["locale"] = "nl" },
    "registration.po"));
Require(poDocument.Entries.Single().Key == "fields.name" && poDocument.Entries.Single().SourcePattern == "Name", "PO import failed");
var xliffAdapter = new Xliff21LocalizationImportAdapter(formatOptions);
var xliffDocument = await xliffAdapter.ParseAsync(new LocalizationImportRequest(
    LocalizationImportFormat.Xliff21,
    Encoding.UTF8.GetBytes("""<?xml version="1.0"?><xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" version="2.1" srcLang="en" trgLang="nl"><file id="f"><unit id="fields.name"><segment><source>Name</source><target>Naam</target></segment></unit></file></xliff>"""),
    LocalizationMergePolicy.ReplaceImported,
    formScope,
    SourceName: "registration.xlf"));
Require(xliffDocument.Entries.Single().Pattern == "Naam", "XLIFF 2.1 import failed");
var xlsxAdapter = new XlsxLocalizationImportAdapter(formatOptions);
var xlsxDocument = await xlsxAdapter.ParseAsync(new LocalizationImportRequest(
    LocalizationImportFormat.Xlsx,
    CreateXlsx(["key", "source", "nl"], ["fields.name", "Name", "Naam"]),
    LocalizationMergePolicy.ReplaceImported,
    formScope,
    new Dictionary<string, string> { ["key"] = "key", ["source"] = "source", ["nl"] = "nl", ["sheet"] = "sheet1" },
    "registration.xlsx"));
Require(xlsxDocument.Entries.Single().Pattern == "Naam", "XLSX import failed");
var exportOptions = new LocalizationExportFormatOptions(MaximumContentBytes: 1_000_000, MaximumRows: 100);
var exportRequest = new LocalizationExportRequest(LocalizationImportFormat.Csv, catalog, formScope, ["nl"], SuggestedBaseName: "registration translations");
var csvExport = await new CsvLocalizationExportAdapter(exportOptions).ExportAsync(exportRequest);
Require(csvExport.ContentSha256.Length == 64 && csvExport.SuggestedFileName == "registration-translations.csv", "CSV export metadata is invalid");
var csvRoundTrip = await csvAdapter.ParseAsync(new LocalizationImportRequest(LocalizationImportFormat.Csv, csvExport.Content, LocalizationMergePolicy.ReplaceImported));
Require(csvRoundTrip.Entries.Single().Scope == formScope && csvRoundTrip.Entries.Single().Pattern == "Identiteit", "structured CSV export/import roundtrip failed");
var typedCatalog = catalog with
{
    Messages = [new LocalizationMessageDefinition("cart.count", formScope, "{count, plural, one {One item} other {# items}}", [new LocalizationArgumentDefinition("count", LocalizationArgumentType.Integer)], [new LocalizedValue("nl", "{count, plural, one {Eén item} other {# items}}", LocalizationValueState.Reviewed)], "Cart item summary", "Checkout")]
};
var typedCsvExport = await new CsvLocalizationExportAdapter(exportOptions).ExportAsync(exportRequest with { Catalog = typedCatalog });
var typedCsvRoundTrip = await csvAdapter.ParseAsync(new LocalizationImportRequest(LocalizationImportFormat.Csv, typedCsvExport.Content, LocalizationMergePolicy.ReplaceImported));
Require(typedCsvRoundTrip.Entries.Single().Arguments is [{ Name: "count", Type: LocalizationArgumentType.Integer }] && typedCsvRoundTrip.Entries.Single().Description == "Cart item summary" && typedCsvRoundTrip.Entries.Single().Context == "Checkout", "CSV export/import lost typed message metadata");
var jsonExport = await new JsonLocalizationExportAdapter(exportOptions).ExportAsync(exportRequest with { Format = LocalizationImportFormat.Json });
var jsonRoundTrip = await jsonAdapter.ParseAsync(new LocalizationImportRequest(LocalizationImportFormat.Json, jsonExport.Content, LocalizationMergePolicy.ReplaceImported));
Require(jsonRoundTrip.Entries.Single().Scope == formScope && jsonRoundTrip.Entries.Single().Arguments?.Count == 0, "JSON export/import roundtrip failed");
var poExport = await new PoLocalizationExportAdapter(exportOptions).ExportAsync(exportRequest with { Format = LocalizationImportFormat.Po });
var poRoundTrip = await poAdapter.ParseAsync(new LocalizationImportRequest(LocalizationImportFormat.Po, poExport.Content, LocalizationMergePolicy.ReplaceImported, formScope, new Dictionary<string, string> { ["locale"] = "nl" }));
Require(poRoundTrip.Entries.Single().Key == "steps.identity", "PO export/import roundtrip failed");
var xliffExport = await new Xliff21LocalizationExportAdapter(exportOptions).ExportAsync(exportRequest with { Format = LocalizationImportFormat.Xliff21 });
var xliffRoundTrip = await xliffAdapter.ParseAsync(new LocalizationImportRequest(LocalizationImportFormat.Xliff21, xliffExport.Content, LocalizationMergePolicy.ReplaceImported, formScope));
Require(xliffRoundTrip.Entries.Single().Pattern == "Identiteit", "XLIFF export/import roundtrip failed");
var formulaCatalog = catalog with { Messages = [message with { Values = [new LocalizedValue("nl", "=2+2", LocalizationValueState.Reviewed, "human")] }] };
var xlsxExporter = new XlsxLocalizationExportAdapter(exportOptions);
var xlsxExportRequest = exportRequest with { Format = LocalizationImportFormat.Xlsx, Catalog = formulaCatalog };
var xlsxExport = await xlsxExporter.ExportAsync(xlsxExportRequest);
var repeatedXlsxExport = await xlsxExporter.ExportAsync(xlsxExportRequest);
Require(xlsxExport.Content.Span.SequenceEqual(repeatedXlsxExport.Content.Span), "XLSX export was not deterministic");
var xlsxRoundTrip = await xlsxAdapter.ParseAsync(new LocalizationImportRequest(LocalizationImportFormat.Xlsx, xlsxExport.Content, LocalizationMergePolicy.ReplaceImported));
Require(xlsxRoundTrip.Entries.Single().Pattern == "=2+2", "XLSX text-only formula defense changed localization data");
var localizationValidator = new LocalizationCatalogValidator();
var localizationDiagnostics = await localizationValidator.ValidateAsync(catalog);
Require(localizationDiagnostics.All(item => item.Severity != LocalizationDiagnosticSeverity.Error), "valid localization catalog was rejected");
var coordinator = new LocalizationImportCoordinator(
    [csvAdapter, jsonAdapter, poAdapter, xliffAdapter, xlsxAdapter],
    localizationValidator,
    new LocalizationImportCoordinatorOptions(10));
var preview = await coordinator.PreviewAsync(catalog, csvRequest);
Require(preview.ContentSha256.Length == 64 && preview.Changes.Count == 2, "hash-bound import preview missing");
Require(preview.Changes.Any(change => change.Key == "steps.identity" && change.Kind == LocalizationImportChangeKind.Preserve), "preserve import effect missing");
Require(preview.Changes.Any(change => change.Key == "fields.email" && change.Kind == LocalizationImportChangeKind.Add), "add import effect missing");
var importMutation = new LocalizationMutationContext(
    "apply-registration-csv",
    LocalizationImportCoordinator.CreateConcurrencyToken(catalog),
    localizationActor,
    DateTimeOffset.UnixEpoch);
var appliedImport = await coordinator.ApplyAsync(catalog, preview.PreviewId, importMutation);
Require(appliedImport.Value.Catalog.Revision.Value == catalog.Revision.Value + 1, "import application did not advance revision");
Require(appliedImport.Value.Catalog.Messages.Any(item => item.Key == "fields.email" && item.Values.Single().Pattern == "E-mailadres"), "import application did not add message");
Require((await coordinator.ApplyAsync(catalog, preview.PreviewId, importMutation)).WasReplay, "import idempotency replay was not detected");
var conflictingRequest = csvRequest with
{
    Content = Encoding.UTF8.GetBytes("key,source,nl\nsteps.identity,Identity,Andere identiteit"),
    MergePolicy = LocalizationMergePolicy.AddOnly
};
var conflictingPreview = await coordinator.PreviewAsync(catalog, conflictingRequest);
Require(conflictingPreview.Changes.Single().Kind == LocalizationImportChangeKind.Conflict, "add-only conflict was not reported");
var missingSourcePreview = await coordinator.PreviewAsync(catalog, csvRequest with
{
    Content = Encoding.UTF8.GetBytes("key,locale,pattern\nfields.phone,nl,Telefoon"),
    Mapping = null
});
Require(missingSourcePreview.Diagnostics.Any(item => item.Code == "PKLI604"), "new import message without a source contract was reviewable");
var digestRejected = false;
try
{
    await csvAdapter.ParseAsync(csvRequest with { ContentSha256 = new string('0', 64) });
}
catch (LocalizationImportFormatException exception) when (exception.Code == "PKLI004")
{
    digestRejected = true;
}
Require(digestRejected, "import digest mismatch was accepted");
await ExpectFormatErrorAsync(
    () => csvAdapter.ParseAsync(csvRequest with { Content = Encoding.UTF8.GetBytes("key,key,nl\nfields.name,Name,Naam") }),
    "PKLI117",
    "duplicate CSV headers were accepted");
await ExpectFormatErrorAsync(
    () => poAdapter.ParseAsync(new LocalizationImportRequest(
        LocalizationImportFormat.Po,
        new byte[] { 0xC3, 0x28 },
        LocalizationMergePolicy.ReplaceImported,
        formScope,
        new Dictionary<string, string> { ["locale"] = "nl" })),
    "PKLI306",
    "invalid PO UTF-8 was accepted");
await ExpectFormatErrorAsync(
    () => jsonAdapter.ParseAsync(new LocalizationImportRequest(
        LocalizationImportFormat.Json,
        Encoding.UTF8.GetBytes("""{"entries":[{"key":"fields.name","languageTag":"nl","pattern":"Naam","arguments":[{"name":"value","type":"String","required":"yes"}]}]}"""),
        LocalizationMergePolicy.ReplaceImported,
        formScope)),
    "PKLI212",
    "non-boolean JSON argument policy was accepted");
await ExpectFormatErrorAsync(
    () => xliffAdapter.ParseAsync(new LocalizationImportRequest(
        LocalizationImportFormat.Xliff21,
        Encoding.UTF8.GetBytes("""<?xml version="1.0"?><!DOCTYPE xliff [<!ENTITY x "unsafe">]><xliff version="2.1" trgLang="nl"><file id="f"><unit id="fields.name"><segment><source>Name</source><target>&x;</target></segment></unit></file></xliff>"""),
        LocalizationMergePolicy.ReplaceImported,
        formScope)),
    "PKLI408",
    "XLIFF DTD content was accepted");
await ExpectFormatErrorAsync(
    () => xlsxAdapter.ParseAsync(new LocalizationImportRequest(
        LocalizationImportFormat.Xlsx,
        CreateXlsx(["key", "source", "nl"], ["fields.name", "Name", "Naam"], includeFormula: true),
        LocalizationMergePolicy.ReplaceImported,
        formScope,
        new Dictionary<string, string> { ["key"] = "key", ["source"] = "source", ["nl"] = "nl" })),
    "PKLI506",
    "XLSX formula content was accepted");
await ExpectFormatErrorAsync(
    () => xlsxAdapter.ParseAsync(new LocalizationImportRequest(
        LocalizationImportFormat.Xlsx,
        CreateXlsx(["key", "source", "nl"], ["fields.name", "Name", "Naam"], includeMacro: true),
        LocalizationMergePolicy.ReplaceImported,
        formScope,
        new Dictionary<string, string> { ["key"] = "key", ["source"] = "source", ["nl"] = "nl" })),
    "PKLI502",
    "XLSX macro content was accepted");
var invalidPlural = new LocalizationMessageDefinition(
    "items",
    new LocalizationScope(LocalizationScopeKind.Application),
    "{count, plural, one {One item}}",
    [new LocalizationArgumentDefinition("count", LocalizationArgumentType.String)],
    []);
var invalidLocalization = catalog with { Messages = [invalidPlural] };
var invalidLocalizationDiagnostics = await localizationValidator.ValidateAsync(invalidLocalization);
Require(invalidLocalizationDiagnostics.Any(item => item.Code == "PKL066"), "plural without other branch was accepted");
Require(invalidLocalizationDiagnostics.Any(item => item.Code == "PKL067"), "plural with nonnumeric argument was accepted");
var localizationRelease = new LocalizationRelease(
    new LocalizationReleaseId("application-v1"),
    catalog.Id,
    catalog.Revision,
    "en",
    catalog.Locales,
    [
        new LocalizationReleaseEntry("steps.identity", formScope, "en", TextDirection.LeftToRight, "Identity", []),
        new LocalizationReleaseEntry("steps.identity", formScope, "nl", TextDirection.LeftToRight, "Identiteit", [])
    ],
    "release-hash",
    DateTimeOffset.UnixEpoch,
    localizationActor);
var localizationRuntime = new InMemoryLocalizationRuntime(localizationRelease);
var localizationCandidate = localizationRelease with
{
    Id = new LocalizationReleaseId("application-v2"),
    Revision = new LocalizationRevision(localizationRelease.Revision.Value + 1),
    Locales = [.. localizationRelease.Locales, new LocaleDefinition("fr", TextDirection.LeftToRight, "en")],
    Entries =
    [
        localizationRelease.Entries[0] with { Pattern = "Identity details" },
        new LocalizationReleaseEntry("steps.identity", formScope, "fr", TextDirection.LeftToRight, "Identité", [])
    ]
};
var releaseDifference = await new DefaultLocalizationReleaseDiffer().CompareAsync(localizationRelease, localizationCandidate);
Require(releaseDifference.HasChanges && !releaseDifference.SourceLocaleChanged, "localization release diff missed candidate changes");
Require(releaseDifference.LocaleDifferences is [{ Kind: LocalizationDifferenceKind.Added, LanguageTag: "fr" }], "localization release locale diff was not deterministic");
Require(releaseDifference.EntryDifferences.Count == 3, "localization release entry diff missed add/change/remove effects");
Require(releaseDifference.EntryDifferences.Any(item => item.Kind == LocalizationDifferenceKind.Changed && item.Key == "steps.identity" && item.LanguageTag == "en"), "localization release pattern change was not reported");
Require(releaseDifference.EntryDifferences.Any(item => item.Kind == LocalizationDifferenceKind.Removed && item.LanguageTag == "nl"), "localization release removal was not reported");
Require(releaseDifference.EntryDifferences.Any(item => item.Kind == LocalizationDifferenceKind.Added && item.LanguageTag == "fr"), "localization release addition was not reported");
var dutchResolution = await localizationRuntime.ResolveAsync(formScope, "steps.identity", "nl");
var fallbackResolution = await localizationRuntime.ResolveAsync(formScope, "steps.identity", "de");
var dutchBundle = await localizationRuntime.GetBundleAsync(formScope, "nl");
Require(dutchResolution?.Pattern == "Identiteit" && dutchResolution.UsedFallback == false, "exact localization resolution failed");
Require(fallbackResolution?.Pattern == "Identity" && fallbackResolution.UsedFallback, "source-locale fallback failed");
Require(dutchBundle?.Messages["steps.identity"] == "Identiteit" && dutchBundle.Sha256.Length == 64, "immutable localization bundle failed");
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
var localizationStorePath = Path.Combine(Path.GetTempPath(), "program-kit-localization-store-" + Guid.NewGuid().ToString("N"));
try
{
    var localizationStore = new FileSystemLocalizationReleaseStore(new FileSystemLocalizationReleaseStoreOptions(localizationStorePath));
    await localizationStore.WriteAsync(localizationRelease);
    await localizationStore.WriteAsync(localizationRelease);
    var storedLocalizationRelease = await localizationStore.GetAsync(localizationRelease.Id);
    Require(storedLocalizationRelease?.CatalogId == catalog.Id, "localization release filesystem roundtrip failed");
    var localizationReleaseCount = 0;
    await foreach (var _ in localizationStore.FindByCatalogAsync(catalog.Id))
    {
        localizationReleaseCount++;
    }

    Require(localizationReleaseCount == 1, "idempotent localization release replay created a duplicate");
    var localizationOverwriteRejected = false;
    try
    {
        await localizationStore.WriteAsync(localizationRelease with { Retired = true });
    }
    catch (InvalidOperationException)
    {
        localizationOverwriteRejected = true;
    }

    Require(localizationOverwriteRejected, "immutable localization release overwrite was accepted");
}
finally
{
    if (Directory.Exists(localizationStorePath))
    {
        Directory.Delete(localizationStorePath, recursive: true);
    }
}
var localizationApplicationPath = Path.Combine(Path.GetTempPath(), "program-kit-localization-application-" + Guid.NewGuid().ToString("N"));
try
{
    var catalogStore = new FileSystemLocalizationCatalogStore(new FileSystemLocalizationCatalogStoreOptions(Path.Combine(localizationApplicationPath, "catalogs")));
    var releaseStore = new FileSystemLocalizationReleaseStore(new FileSystemLocalizationReleaseStoreOptions(Path.Combine(localizationApplicationPath, "releases")));
    var applicationCoordinator = new LocalizationImportCoordinator([csvAdapter], localizationValidator, new LocalizationImportCoordinatorOptions(10));
    var application = new DefaultLocalizationCatalogService(catalogStore, releaseStore, releaseStore, localizationValidator, applicationCoordinator);
    var managedCatalog = catalog with
    {
        Id = new LocalizationCatalogId("managed"),
        Revision = new LocalizationRevision(1),
        State = LocalizationLifecycleState.Draft,
        Messages = [message with { Values = [new LocalizedValue("nl", "Identiteit", LocalizationValueState.Approved, "human")] }]
    };
    var createMutation = new LocalizationMutationContext("managed-create", null, localizationActor, DateTimeOffset.Parse("2026-01-01T00:00:00Z"));
    var createdCatalog = await application.CreateAsync(managedCatalog, createMutation);
    Require(createdCatalog.Version.Value.Length == 64 && !createdCatalog.WasReplay, "managed catalog create did not return an opaque version");
    Require((await application.CreateAsync(managedCatalog, createMutation)).WasReplay, "managed catalog create was not durably idempotent");
    var keyReuseRejected = false;
    try
    {
        await application.CreateAsync(managedCatalog with { Name = "Different command" }, createMutation);
    }
    catch (InvalidOperationException)
    {
        keyReuseRejected = true;
    }

    Require(keyReuseRejected, "managed catalog idempotency-key reuse was accepted");
    var staleReplaceRejected = false;
    try
    {
        await application.ReplaceAsync(managedCatalog with { Revision = new LocalizationRevision(2) }, createMutation with { IdempotencyKey = "managed-stale-replace", ExpectedVersion = new LocalizationConcurrencyToken("stale") });
    }
    catch (InvalidOperationException)
    {
        staleReplaceRejected = true;
    }

    Require(staleReplaceRejected, "managed catalog stale replacement was accepted");
    var managedImport = csvRequest with { Content = Encoding.UTF8.GetBytes("key,source,nl\nsteps.identity,Identity,Identiteit\nfields.email,Email,E-mailadres") };
    var managedPreview = await application.PreviewImportAsync(managedCatalog.Id, managedImport);
    var applyMutation = new LocalizationMutationContext("managed-import", createdCatalog.Version, localizationActor, DateTimeOffset.Parse("2026-01-02T00:00:00Z"));
    var importedCatalog = await application.ApplyImportAsync(managedCatalog.Id, managedPreview.PreviewId, applyMutation);
    Require(importedCatalog.Value.Revision.Value == 2 && importedCatalog.Value.Messages.Count == 2, "managed import did not persist the next draft revision");
    var restartedApplication = new DefaultLocalizationCatalogService(
        new FileSystemLocalizationCatalogStore(new FileSystemLocalizationCatalogStoreOptions(Path.Combine(localizationApplicationPath, "catalogs"))),
        new FileSystemLocalizationReleaseStore(new FileSystemLocalizationReleaseStoreOptions(Path.Combine(localizationApplicationPath, "releases"))),
        new FileSystemLocalizationReleaseStore(new FileSystemLocalizationReleaseStoreOptions(Path.Combine(localizationApplicationPath, "releases"))),
        localizationValidator,
        new LocalizationImportCoordinator([csvAdapter], localizationValidator, new LocalizationImportCoordinatorOptions(10)));
    Require((await restartedApplication.ApplyImportAsync(managedCatalog.Id, managedPreview.PreviewId, applyMutation)).WasReplay, "managed import replay did not survive application restart");
    var reviewMutation = new LocalizationMutationContext("managed-review", importedCatalog.Version, localizationActor, DateTimeOffset.Parse("2026-01-03T00:00:00Z"));
    var reviewedCatalog = await application.SubmitForReviewAsync(managedCatalog.Id, importedCatalog.Value.Revision, reviewMutation);
    Require(reviewedCatalog.Value == LocalizationLifecycleState.InReview, "managed catalog did not enter review");
    Require((await restartedApplication.SubmitForReviewAsync(managedCatalog.Id, importedCatalog.Value.Revision, reviewMutation)).WasReplay, "review replay did not survive application restart");
    var approveMutation = new LocalizationMutationContext("managed-approve", reviewedCatalog.Version, localizationActor, DateTimeOffset.Parse("2026-01-04T00:00:00Z"));
    var approvedCatalog = await application.ApproveAsync(managedCatalog.Id, importedCatalog.Value.Revision, approveMutation);
    Require(approvedCatalog.Value == LocalizationLifecycleState.Approved, "managed catalog did not enter approved state");
    var publishMutation = new LocalizationMutationContext("managed-publish", approvedCatalog.Version, localizationActor, DateTimeOffset.Parse("2026-01-05T00:00:00Z"));
    var publishedCatalog = await application.PublishAsync(managedCatalog.Id, importedCatalog.Value.Revision, publishMutation);
    Require(publishedCatalog.Value.Sha256.Length == 64 && publishedCatalog.Value.Entries.Count == 3, "managed publication did not produce deterministic approved content");
    Require((await restartedApplication.PublishAsync(managedCatalog.Id, importedCatalog.Value.Revision, publishMutation)).WasReplay, "publication replay did not survive application restart");
    var foundCatalogs = await application.FindAsync("MANAGED", maximum: 10);
    Require(foundCatalogs.Total == 1 && foundCatalogs.Items.Single().State == LocalizationLifecycleState.Published, "bounded managed catalog query failed");
    var managedDocument = await application.GetCatalogAsync(managedCatalog.Id);
    Require(managedDocument?.Version == publishedCatalog.Version && managedDocument.Catalog.State == LocalizationLifecycleState.Published, "managed catalog detail did not expose its current mutation version");
    var persistedCatalog = await catalogStore.GetAsync(managedCatalog.Id);
    Require(persistedCatalog?.AuditTrail.Count == 5 && persistedCatalog.AuditTrail.All(item => item.Actor.Id == localizationActor.Id), "managed catalog audit history was not durable or claim-attributed");
    var retireMutation = new LocalizationMutationContext("managed-retire", new LocalizationConcurrencyToken(publishedCatalog.Value.Sha256), localizationActor, DateTimeOffset.Parse("2026-01-06T00:00:00Z"));
    var retiredRelease = await application.RetireAsync(publishedCatalog.Value.Id, retireMutation);
    Require(retiredRelease.Value.Retired && !retiredRelease.WasReplay, "managed release retirement failed");
    Require((await restartedApplication.RetireAsync(publishedCatalog.Value.Id, retireMutation)).WasReplay, "release retirement replay did not survive application restart");
    Require((await application.GetReleaseAsync(publishedCatalog.Value.Id))?.Retired == true, "release query did not apply separate retirement state");

    var incompleteCatalog = managedCatalog with
    {
        Id = new LocalizationCatalogId("incomplete"),
        Locales = [managedCatalog.Locales[0], managedCatalog.Locales[1] with { RequiredForPublication = true }],
        Messages = [message]
    };
    var incompleteCreated = await application.CreateAsync(incompleteCatalog, new LocalizationMutationContext("incomplete-create", null, localizationActor, DateTimeOffset.Parse("2026-02-01T00:00:00Z")));
    var incompleteReviewed = await application.SubmitForReviewAsync(incompleteCatalog.Id, incompleteCatalog.Revision, new LocalizationMutationContext("incomplete-review", incompleteCreated.Version, localizationActor, DateTimeOffset.Parse("2026-02-02T00:00:00Z")));
    var incompleteApproved = await application.ApproveAsync(incompleteCatalog.Id, incompleteCatalog.Revision, new LocalizationMutationContext("incomplete-approve", incompleteReviewed.Version, localizationActor, DateTimeOffset.Parse("2026-02-03T00:00:00Z")));
    var incompletePublicationRejected = false;
    try
    {
        await application.PublishAsync(incompleteCatalog.Id, incompleteCatalog.Revision, new LocalizationMutationContext("incomplete-publish", incompleteApproved.Version, localizationActor, DateTimeOffset.Parse("2026-02-04T00:00:00Z")));
    }
    catch (InvalidOperationException)
    {
        incompletePublicationRejected = true;
    }

    Require(incompletePublicationRejected, "required locale without an approved value was published");
    Require((await application.GetCatalogAsync(incompleteCatalog.Id))?.Catalog.State == LocalizationLifecycleState.Approved, "failed publication changed catalog lifecycle state");
    var enumerationLimitRejected = false;
    try
    {
        var boundedCatalogStore = new FileSystemLocalizationCatalogStore(new FileSystemLocalizationCatalogStoreOptions(Path.Combine(localizationApplicationPath, "catalogs"), MaximumCatalogs: 1));
        await foreach (var _ in boundedCatalogStore.FindAsync())
        {
        }
    }
    catch (InvalidDataException)
    {
        enumerationLimitRejected = true;
    }

    Require(enumerationLimitRejected, "filesystem catalog enumeration exceeded its configured bound");
    var catalogFile = Directory.GetFiles(Path.Combine(localizationApplicationPath, "catalogs"), "*.localization-catalog.json").First();
    var catalogContent = await File.ReadAllTextAsync(catalogFile, Encoding.UTF8);
    var digestOffset = catalogContent.IndexOf("\"sha256\":\"", StringComparison.Ordinal) + 10;
    Require(digestOffset >= 10, "catalog digest envelope was not written");
    var replacement = catalogContent[digestOffset] == '0' ? '1' : '0';
    await File.WriteAllTextAsync(catalogFile, catalogContent[..digestOffset] + replacement + catalogContent[(digestOffset + 1)..], Encoding.UTF8);
    var catalogTamperRejected = false;
    try
    {
        await foreach (var _ in catalogStore.FindAsync())
        {
        }
    }
    catch (InvalidDataException)
    {
        catalogTamperRejected = true;
    }

    Require(catalogTamperRejected, "tampered localization catalog envelope was accepted");
}
finally
{
    if (Directory.Exists(localizationApplicationPath))
    {
        Directory.Delete(localizationApplicationPath, recursive: true);
    }
}
Require(typeof(IFormAuthoring).Assembly.GetReferencedAssemblies().All(IsAllowedDependency), "forms contract leaked an implementation dependency");
Require(typeof(ILocalizationRuntime).Assembly.GetReferencedAssemblies().All(IsAllowedDependency), "localization contract leaked an implementation dependency");

Console.WriteLine("Forms/localization probe passed: validation, deterministic compilation, wizard, ICU localization, fallback, hostile import and deterministic export formats, hash-bound import, durable application lifecycle, release diff, immutable storage, compatibility, and dependency isolation.");

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

static byte[] CreateXlsx(
    IReadOnlyList<string> headers,
    IReadOnlyList<string> values,
    bool includeFormula = false,
    bool includeMacro = false)
{
    using var output = new MemoryStream();
    using (var archive = new ZipArchive(output, ZipArchiveMode.Create, leaveOpen: true))
    {
        var entry = archive.CreateEntry("xl/worksheets/sheet1.xml", CompressionLevel.NoCompression);
        using (var writer = new StreamWriter(entry.Open(), new UTF8Encoding(false)))
        {
            writer.Write("<?xml version=\"1.0\" encoding=\"utf-8\"?><worksheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"><sheetData>");
            WriteRow(writer, 1, headers);
            WriteRow(writer, 2, values, includeFormula);
            writer.Write("</sheetData></worksheet>");
        }
        if (includeMacro)
        {
            archive.CreateEntry("xl/vbaProject.bin", CompressionLevel.NoCompression);
        }
    }
    return output.ToArray();
}

static void WriteRow(TextWriter writer, int number, IReadOnlyList<string> values, bool includeFormula = false)
{
    writer.Write($"<row r=\"{number}\">");
    for (var index = 0; index < values.Count; index++)
    {
        var column = (char)('A' + index);
        if (includeFormula && index == values.Count - 1)
        {
            writer.Write($"<c r=\"{column}{number}\"><f>NOW()</f><v>0</v></c>");
        }
        else
        {
            writer.Write($"<c r=\"{column}{number}\" t=\"inlineStr\"><is><t>{System.Security.SecurityElement.Escape(values[index])}</t></is></c>");
        }
    }
    writer.Write("</row>");
}

static async ValueTask ExpectFormatErrorAsync(
    Func<ValueTask<LocalizationImportDocument>> action,
    string code,
    string message)
{
    try
    {
        await action();
    }
    catch (LocalizationImportFormatException exception) when (exception.Code == code)
    {
        return;
    }
    throw new InvalidOperationException(message);
}

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
