import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { compileBuildTimeValidator, generateStandaloneValidatorModule } from "@orbyss-io/forms-ajv-build";
import { defaultRuntimeLimits } from "@orbyss-io/forms-contracts";
import { jsonEditorIndentationPolicy, normalizeJsonEditorDiagnostics, requireJsonEditorOptions } from "@orbyss-io/forms-editor-contracts";
import {
  createJsonFormsTranslator,
  createJsonFormsTranslatorAdapter,
  createPrecompiledJsonFormsAjvFacade,
  jsonFormsValidationErrorsToIssues,
  prepareJsonFormsRuntime
} from "@orbyss-io/forms-jsonforms-runtime";
import { FormLookupController, FormLookupRegistry } from "@orbyss-io/forms-lookups";
import { FormActionRegistry, RendererRegistry } from "@orbyss-io/forms-renderer-registry";
import { OrbyssActionController, OrbyssActionError, parseOrbyssActionBar } from "@orbyss-io/forms-actions";
import { OrbyssWizardController, parseOrbyssWizard } from "@orbyss-io/forms-wizard";
import { OrbyssJsonForms } from "@orbyss-io/forms-react";
import { rankWith, uiTypeIs } from "@jsonforms/core";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createSSRApp, defineComponent, h, markRaw } from "vue";
import { renderToString } from "vue/server-renderer";
import {
  OrbyssJsonFormsVue,
  programKitVueFormsAdapterVersion
} from "@orbyss-io/forms-vue";
import {
  joinOrbyssClassNames,
  programKitClassName,
  programKitThemeTokenNames
} from "@orbyss-io/forms-ui-theme";

const schema = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "urn:orbyss:forms:registration:1",
  type: "object",
  properties: { name: { type: "string", minLength: 1 } },
  required: ["name"],
  additionalProperties: false
};
const uiSchema = {
  type: "Categorization",
  id: "registration",
  options: { variant: "orbyss-forms-wizard" },
  elements: [{ type: "Category", id: "identity", elements: [{ type: "Control", id: "name", scope: "#/properties/name" }] }]
};

function artifact(mediaType, value) {
  const content = JSON.stringify(value);
  return { mediaType, content, sha256: createHash("sha256").update(content).digest("hex") };
}

function release(overrides = {}) {
  return {
    id: { value: "registration-v1" },
    candidate: {
      formId: { value: "registration" },
      revision: { value: 1 },
      dataSchema: artifact("application/schema+json", schema),
      uiSchema: artifact("application/vnd.jsonforms.uischema+json", uiSchema),
      renderers: [{ componentId: "Orbyss.Forms.Wizard", versionRange: "[1.0.0,2.0.0)" }],
      translations: [],
      actions: [{
        actionId: "finish",
        handlerId: "registration.submit",
        kind: "submit",
        label: { key: "actions.finish", defaultText: "Finish" },
        requiresValidForm: true
      }],
      diagnostics: [],
      compiledAt: "2026-09-06T00:00:00Z",
      candidateSha256: "candidate"
    },
    publishedAt: "2026-09-06T00:00:00Z",
    evidence: ["acceptance"],
    retired: false,
    ...overrides
  };
}

test("AJV build-time validator agrees with the generated schema", () => {
  const validate = compileBuildTimeValidator(schema);
  assert.deepEqual(validate({ name: "Ada" }), []);
  assert.equal(validate({ name: "" }).some(issue => issue.keyword === "minLength"), true);
  assert.equal(validate({ name: "Ada", executable: true }).some(issue => issue.keyword === "additionalProperties"), true);
});

test("AJV allowlists Orbyss Forms annotations while rejecting arbitrary schema extensions", () => {
  assert.deepEqual(compileBuildTimeValidator({
    type: "string",
    "x-i18n": "fields.name",
    "x-description-i18n": "fields.name.description"
  })("Ada"), []);
  assert.throws(() => compileBuildTimeValidator({ type: "string", "x-executable": "forbidden" }), /unknown keyword/);
});

test("AJV emits an executable standalone ESM validator without runtime code generation", async () => {
  const helperFreeSchema = {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    type: "object",
    properties: { name: { type: "string" } },
    required: ["name"],
    additionalProperties: false
  };
  const source = generateStandaloneValidatorModule(helperFreeSchema);
  assert.doesNotMatch(source, /\beval\s*\(|new\s+Function\b/);
  const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`;
  const generated = await import(moduleUrl);
  assert.equal(generated.validate({ name: "Ada" }), true);
  assert.equal(generated.validate({}), false);
});

test("runtime verifies artifacts, renderer requirements, translations, and typed actions", async () => {
  const renderers = new RendererRegistry([{ componentId: "Orbyss.Forms.Wizard", version: "1.0.0", rank: ui => ui.type === "Categorization" ? 10 : -1, renderer: "wizard" }]);
  const actions = new FormActionRegistry({
    "registration.submit": async (payload, context) => ({ payload, formId: context.formId, releaseId: context.releaseId })
  });
  const validate = compileBuildTimeValidator(schema);
  const translate = createJsonFormsTranslator({ "name.label": "Naam" });
  const runtime = await prepareJsonFormsRuntime(release(), renderers, actions, validate, translate);
  assert.equal(runtime.renderers.resolve(uiSchema, schema), "wizard");
  assert.equal(runtime.translate("name.label", "Name"), "Naam");
  assert.equal(runtime.translate("missing", "Fallback"), "Fallback");
  assert.deepEqual(runtime.validate({ name: "Ada" }), []);
  const result = await runtime.dispatchAction("finish", { name: "Ada" }, { signal: new AbortController().signal });
  assert.deepEqual(result, { payload: { name: "Ada" }, formId: "registration", releaseId: "registration-v1" });
  await assert.rejects(() => runtime.dispatchAction("undeclared", {}, { signal: new AbortController().signal }), /not declared/);
});

test("framework adapters share a precompiled JSON Forms validation facade", () => {
  const validate = compileBuildTimeValidator(schema);
  const facade = createPrecompiledJsonFormsAjvFacade(schema, validate);
  const root = facade.compile(schema);
  assert.equal(root({ name: "Ada" }), true);
  assert.equal(root({}), false);
  assert.equal(root.errors?.[0]?.keyword, "required");
  assert.equal(root.errors?.[0]?.params.missingProperty, "name");
  const translate = createJsonFormsTranslatorAdapter((key, fallback) => key === "error.required" ? "Required" : fallback);
  assert.equal(translate("fields.name", "Name"), "Name");
  assert.equal(translate("error.required"), "Required");
  assert.equal(translate("error.minimum"), undefined);

  const condition = { properties: { enabled: { const: true } }, required: ["enabled"] };
  assert.equal(facade.validate(condition, { enabled: true }), true);
  assert.equal(facade.validate(condition, { enabled: false }), false);
  const compiledCondition = facade.compile(condition);
  assert.equal(compiledCondition({ enabled: false }), false);
  assert.equal(compiledCondition.errors?.[0]?.keyword, "condition");
  assert.throws(() => facade.validate({ pattern: "^unsafe-to-compile$" }, "value"), /requires a precompiled validator/);

  assert.deepEqual(jsonFormsValidationErrorsToIssues([{
    instancePath: "",
    keyword: "required",
    message: "must have required property 'name'",
    params: { missingProperty: "name" }
  }]), [{
    path: "",
    keyword: "required",
    message: "must have required property 'name'",
    property: "name"
  }]);
});

test("Vue binding renders a governed runtime through consumer-supplied renderers", async () => {
  const RootRenderer = defineComponent({
    name: "OrbyssVueTestRenderer",
    setup: () => () => h("output", { "data-vue-runtime": "ready" }, "Vue runtime ready")
  });
  const runtime = {
    schema,
    uiSchema,
    validate: compileBuildTimeValidator(schema),
    translate: (_key, fallback) => fallback
  };
  const application = createSSRApp({
    render: () => h(OrbyssJsonFormsVue, {
      runtime,
      data: { name: "Ada" },
      renderers: [{ tester: () => 1000, renderer: markRaw(RootRenderer) }]
    })
  });
  const markup = await renderToString(application);
  assert.equal(programKitVueFormsAdapterVersion, "1.0.0");
  assert.match(markup, /data-vue-runtime="ready"/);
  assert.match(markup, /Vue runtime ready/);
});

test("TypeScript runtime consumes the exact release fixture emitted by the .NET compiler", async () => {
  const compiledRelease = JSON.parse(await readFile(
    new URL("./fixtures/dotnet-registration-release.json", import.meta.url),
    "utf8"
  ));
  const renderers = new RendererRegistry([
    { componentId: "Orbyss.Forms.ActionBar", version: "1.0.0", rank: ui => ui.type === "Orbyss.Forms.ActionBar" ? 1000 : -1, renderer: "actions" },
    { componentId: "Orbyss.Forms.Wizard", version: "1.0.0", rank: ui => ui.type === "Categorization" ? 1000 : -1, renderer: "wizard" }
  ]);
  const actions = new FormActionRegistry({
    "registration.submit": async payload => ({ accepted: true, payload })
  });
  const runtime = await prepareJsonFormsRuntime(
    compiledRelease,
    renderers,
    actions,
    compileBuildTimeValidator(JSON.parse(compiledRelease.candidate.dataSchema.content)),
    (_key, fallback) => fallback
  );
  assert.doesNotMatch(
    generateStandaloneValidatorModule(JSON.parse(compiledRelease.candidate.dataSchema.content)),
    /\beval\s*\(|new\s+Function\b/
  );
  const actionElement = runtime.uiSchema.elements[0].elements[1];
  const actionBar = parseOrbyssActionBar(actionElement, runtime.actions);
  assert.deepEqual(actionBar.actions.map(action => action.actionId), ["finish"]);
  assert.equal(actionBar.actions[0].requiresValidForm, true);
  assert.deepEqual(
    await runtime.dispatchAction("finish", { name: "Ada" }, { signal: new AbortController().signal }),
    { accepted: true, payload: { name: "Ada" } }
  );
});

test("action bars preserve release order and reject undeclared or duplicate actions", () => {
  const requirements = [
    {
      actionId: "save",
      handlerId: "registration.save",
      kind: "saveDraft",
      label: { key: "actions.save", defaultText: "Save draft" },
      requiresValidForm: false
    },
    {
      actionId: "submit",
      handlerId: "registration.submit",
      kind: "submit",
      label: { key: "actions.submit", defaultText: "Submit" },
      requiresValidForm: true,
      icon: { name: "send", bundle: "lucide" }
    }
  ];
  const definition = parseOrbyssActionBar({
    type: "Orbyss.Forms.ActionBar",
    id: "primary-actions",
    options: { actions: ["submit", "save"] }
  }, requirements);
  assert.deepEqual(definition.actions.map(action => action.actionId), ["submit", "save"]);
  assert.equal(definition.actions[0].position, 0);
  assert.throws(() => parseOrbyssActionBar({
    type: "Orbyss.Forms.ActionBar",
    options: { actions: ["missing"] }
  }, requirements), /absent from the immutable release manifest/);
  assert.throws(() => parseOrbyssActionBar({
    type: "Orbyss.Forms.ActionBar",
    options: { actions: ["save", "save"] }
  }, requirements), /repeated/);
});

test("action controller gates validation, availability, and global single-flight dispatch", async () => {
  const definition = parseOrbyssActionBar({
    type: "Orbyss.Forms.ActionBar",
    options: { actions: ["submit", "save", "hidden"] }
  }, [
    { actionId: "submit", handlerId: "submit", kind: "submit", label: { key: "submit", defaultText: "Submit" }, requiresValidForm: true },
    { actionId: "save", handlerId: "save", kind: "saveDraft", label: { key: "save", defaultText: "Save" }, requiresValidForm: false },
    { actionId: "hidden", handlerId: "hidden", kind: "custom", label: { key: "hidden", defaultText: "Hidden" }, requiresValidForm: false }
  ]);
  let valid = false;
  let resolveDispatch;
  let dispatchCount = 0;
  const controller = new OrbyssActionController(definition, {
    validate: () => valid ? [] : [{ path: "/name", keyword: "required", message: "Name is required." }],
    availability: action => action.actionId === "hidden" ? "hidden" : "enabled",
    dispatch: async () => {
      dispatchCount += 1;
      return await new Promise(resolve => { resolveDispatch = resolve; });
    }
  });

  const blocked = await controller.invoke("submit", {}, { data: {} });
  assert.equal(blocked.reason, "validation");
  assert.equal(blocked.issues.length, 1);
  assert.equal(dispatchCount, 0);
  assert.equal((await controller.invoke("hidden", {}, { data: {} })).reason, "hidden");
  valid = true;
  const running = controller.invoke("save", {}, { data: {} });
  assert.equal((await controller.invoke("submit", {}, { data: {} })).reason, "busy");
  resolveDispatch({ saved: true });
  const saved = await running;
  assert.equal(saved.invoked, true);
  assert.equal(saved.snapshot.runningActionId, undefined);
  assert.equal(saved.snapshot.actions.find(action => action.actionId === "save").status, "succeeded");
  assert.equal(dispatchCount, 1);
});

test("action controller exposes only deliberate public failures and supports cancellation", async () => {
  const definition = parseOrbyssActionBar({ type: "Orbyss.Forms.ActionBar", options: { actions: ["run"] } }, [{
    actionId: "run",
    handlerId: "run",
    kind: "custom",
    label: { key: "run", defaultText: "Run" },
    requiresValidForm: false
  }]);
  const explicit = new OrbyssActionController(definition, {
    validate: () => [],
    dispatch: async () => { throw new OrbyssActionError("PAYMENT_DECLINED", "Payment was declined.", true); }
  });
  const explicitResult = await explicit.invoke("run", {}, { data: {} });
  assert.deepEqual(explicitResult.snapshot.actions[0].failure, {
    code: "PAYMENT_DECLINED", message: "Payment was declined.", retryable: true
  });

  const unexpected = new OrbyssActionController(definition, {
    validate: () => [],
    dispatch: async () => { throw new Error("database password leaked"); }
  });
  const unexpectedResult = await unexpected.invoke("run", {}, { data: {} });
  assert.deepEqual(unexpectedResult.snapshot.actions[0].failure, {
    code: "PKA999", message: "The action could not be completed.", retryable: false
  });

  const cancellable = new OrbyssActionController(definition, {
    validate: () => [],
    dispatch: async (_id, _payload, signal) => await new Promise((_resolve, reject) => {
      signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    })
  });
  const pending = cancellable.invoke("run", {}, { data: {} });
  assert.equal(cancellable.cancel(), true);
  const cancelled = await pending;
  assert.equal(cancelled.reason, "cancelled");
  assert.equal(cancelled.snapshot.actions[0].status, "cancelled");
});

test("theme contract exposes bounded semantic tokens and deterministic class composition", () => {
  assert.equal(programKitThemeTokenNames.includes("--pk-color-primary"), true);
  assert.equal(programKitThemeTokenNames.includes("--pk-shadow-dialog"), true);
  assert.equal(new Set(programKitThemeTokenNames).size, programKitThemeTokenNames.length);
  assert.equal(joinOrbyssClassNames("base repeated", "repeated consumer"), "base repeated consumer");
  assert.equal(programKitClassName("pk-default", "consumer", false), "pk-default consumer");
  assert.equal(programKitClassName("pk-default", "consumer", true), "consumer");
});

test("searchable lookups enforce provider contracts, paging, filters, and label rehydration", async () => {
  const registry = new FormLookupRegistry([{
    contract: {
      dataSourceId: "catalog.products",
      contractVersion: "1.0.0",
      displayName: "Products",
      providerPackage: "@orbyss-io/orbyss-forms-product-lookups",
      execution: "server",
      supportsSearch: true,
      supportsPaging: true,
      filterKeys: ["countryId"],
      maximumPageSize: 2
    },
    search: async query => query.cursor === undefined
      ? { items: [{ value: "p1", label: `One ${query.filters.countryId}` }, { value: "p2", label: "Two" }], nextCursor: "page-2" }
      : { items: [{ value: "p2", label: "Two" }, { value: "p3", label: "Three" }] },
    resolve: async values => values.map(value => ({ value, label: `Resolved ${value}` }))
  }]);
  const controller = new FormLookupController({
    registry,
    dataSourceId: "catalog.products",
    locale: "en",
    minimumCharacters: 1,
    debounceMilliseconds: 0,
    pageSize: 2
  });
  const first = await controller.search("pro", { countryId: "nl" });
  assert.deepEqual(first.items.map(item => item.value), ["p1", "p2"]);
  assert.equal(first.items[0].label, "One nl");
  const second = await controller.loadMore();
  assert.deepEqual(second.items.map(item => item.value), ["p1", "p2", "p3"], "paging must deduplicate stable values");
  assert.deepEqual(await controller.resolve(["p3"]), [{ value: "p3", label: "Resolved p3" }]);
  await assert.rejects(() => registry.search({ dataSourceId: "catalog.products", search: "x", pageSize: 2, filters: { undeclared: true } }, { signal: new AbortController().signal, locale: "en" }), /undeclared filter/);
});

test("searchable lookups cancel superseded searches and hide unexpected provider details", async () => {
  const registry = new FormLookupRegistry([{
    contract: {
      dataSourceId: "catalog.slow",
      contractVersion: "1.0.0",
      displayName: "Slow catalog",
      execution: "server",
      supportsSearch: true,
      supportsPaging: false,
      filterKeys: [],
      maximumPageSize: 10
    },
    search: async (_query, context) => await new Promise((_resolve, reject) => {
      context.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    }),
    resolve: async () => { throw new Error("private upstream token"); }
  }]);
  const controller = new FormLookupController({ registry, dataSourceId: "catalog.slow", locale: "en", minimumCharacters: 1, debounceMilliseconds: 0 });
  const pending = controller.search("first");
  await Promise.resolve();
  assert.equal(controller.cancel(), true);
  await pending;
  assert.equal(controller.snapshot().status, "idle");
  const failingRegistry = new FormLookupRegistry([{
    ...registry.list().map(contract => ({ contract }))[0],
    search: async () => { throw new Error("private upstream token"); },
    resolve: async () => []
  }]);
  const failing = new FormLookupController({ registry: failingRegistry, dataSourceId: "catalog.slow", locale: "en", minimumCharacters: 1, debounceMilliseconds: 0 });
  const result = await failing.search("fail");
  assert.deepEqual(result.failure, { code: "PKLU999", message: "Options could not be loaded.", retryable: true });
  assert.equal(JSON.stringify(result).includes("private upstream token"), false);
  await assert.rejects(() => new FormLookupController({ registry, dataSourceId: "catalog.slow", locale: "en" }).resolve(["x"]), error => error.message === "Options could not be loaded.");
});

test("runtime fails closed for tampering, external references, and missing renderers", async () => {
  const emptyRenderers = new RendererRegistry([]);
  const actions = new FormActionRegistry({});
  const validate = compileBuildTimeValidator(schema);
  const tampered = release();
  tampered.candidate.dataSchema.content += " ";
  await assert.rejects(() => prepareJsonFormsRuntime(tampered, emptyRenderers, actions, validate, (_key, fallback) => fallback), /SHA-256/);

  const externalSchema = { ...schema, properties: { address: { $ref: "https://example.test/address.json" } } };
  const external = release();
  external.candidate.dataSchema = artifact("application/schema+json", externalSchema);
  await assert.rejects(() => prepareJsonFormsRuntime(external, emptyRenderers, actions, validate, (_key, fallback) => fallback), /must be bundled/);

  await assert.rejects(() => prepareJsonFormsRuntime(release(), emptyRenderers, actions, validate, (_key, fallback) => fallback), /not installed/);
});

test("runtime refuses to render a release whose trusted action package is not installed", async () => {
  const renderers = new RendererRegistry([
    { componentId: "Orbyss.Forms.Wizard", version: "1.0.0", rank: () => 1, renderer: "wizard" }
  ]);
  await assert.rejects(() => prepareJsonFormsRuntime(
    release(),
    renderers,
    new FormActionRegistry({}),
    compileBuildTimeValidator(schema),
    (_key, fallback) => fallback
  ), /Required action handler 'registration.submit' is not registered/);
});

test("default runtime bounds and application-owned JSON editor contracts stay independently consumable", () => {
  assert.equal(defaultRuntimeLimits.maximumArtifactBytes, 1_048_576);
  assert.deepEqual(jsonEditorIndentationPolicy, { insertSpaces: true, tabSize: 2, tabKeyIndents: true, focusNavigationToggle: "Ctrl+M" });
  assert.throws(() => requireJsonEditorOptions({ parent: {}, document: "{}", accessibleLabel: " " }), /accessible label/);
  assert.deepEqual(normalizeJsonEditorDiagnostics([
    { from: -3, to: 99, severity: "error", message: "Invalid document" }
  ], 4), [{ from: 0, to: 4, severity: "error", message: "Invalid document" }]);
  assert.throws(() => normalizeJsonEditorDiagnostics([
    { from: 0, to: 0, severity: "fatal", message: "Invalid severity" }
  ], 0), /unsupported severity/);
});

test("Orbyss Forms wizard parses translated labels, icons, and portable presentation policy", () => {
  const definition = parseOrbyssWizard({
    type: "Categorization",
    id: "checkout",
    options: {
      variant: "orbyss-forms-wizard",
      navigationPolicy: "visited",
      navigationPlacement: "top",
      progressStyle: "segmented",
      validateBeforeAdvance: true,
      saveProgress: true,
      deepLink: true
    },
    elements: [
      { type: "Category", id: "identity", label: "Identity", i18n: "steps.identity", options: { icon: { name: "user", bundle: "lucide" } }, elements: [] },
      { type: "Category", id: "preferences", label: "Preferences", options: { presentation: { optional: "true" } }, elements: [] },
      { type: "Category", id: "confirm", label: "Confirm", elements: [] }
    ]
  }, (key, fallback) => key === "steps.identity" ? "Identiteit" : fallback);

  assert.equal(definition.navigationPolicy, "visited");
  assert.equal(definition.navigationPlacement, "top");
  assert.equal(definition.progressStyle, "segmented");
  assert.equal(definition.saveProgress, true);
  assert.equal(definition.deepLink, true);
  assert.equal(definition.steps[0].label, "Identiteit");
  assert.deepEqual(definition.steps[0].icon, { name: "user", bundle: "lucide" });
  assert.equal(definition.steps[1].optional, true);
});

test("Orbyss Forms wizard gates forward movement, supports optional steps, and retains stable state", async () => {
  const definition = parseOrbyssWizard({
    type: "Categorization",
    id: "checkout",
    options: { variant: "orbyss-forms-wizard", navigationPolicy: "linear", validateBeforeAdvance: true },
    elements: [
      { type: "Category", id: "identity", label: "Identity", elements: [] },
      { type: "Category", id: "preferences", label: "Preferences", options: { presentation: { optional: "true" } }, elements: [] },
      { type: "Category", id: "confirm", label: "Confirm", elements: [] }
    ]
  });
  let identityValid = false;
  const controller = new OrbyssWizardController(definition, {
    validateStep: async stepId => stepId === "identity" && !identityValid
      ? [{ stepId, path: "/name", message: "Name is required.", severity: "error" }]
      : []
  });

  assert.equal((await controller.select("confirm")).reason, "policy");
  const blocked = await controller.next();
  assert.equal(blocked.reason, "validation");
  assert.equal(blocked.snapshot.steps[0].status, "error");
  identityValid = true;
  assert.equal((await controller.next()).snapshot.currentStepId, "preferences");
  const skipped = controller.skip();
  assert.equal(skipped.snapshot.currentStepId, "confirm");
  assert.equal(skipped.snapshot.steps[1].status, "skipped");
  assert.equal(controller.back().snapshot.currentStepId, "preferences");
  assert.equal(controller.updateVisibleSteps(["identity", "confirm"]).currentStepId, "confirm");
  const finished = await controller.finish();
  assert.equal(finished.moved, true);
  assert.equal(finished.snapshot.completed, true);
  assert.equal(finished.snapshot.progress, 1);
});

test("Orbyss Forms wizard rejects malformed and duplicate categories", () => {
  assert.throws(() => parseOrbyssWizard({ type: "VerticalLayout", options: {}, elements: [] }), /Categorization/);
  assert.throws(() => parseOrbyssWizard({
    type: "Categorization",
    options: { variant: "orbyss-forms-wizard" },
    elements: [
      { type: "Category", id: "same", elements: [] },
      { type: "Category", id: "same", elements: [] }
    ]
  }), /Duplicate wizard step/);
});

test("React binding delegates all rendering to the consuming application", () => {
  const controlUiSchema = { type: "Control", scope: "#/properties/name" };
  const runtime = {
    schema,
    uiSchema: controlUiSchema,
    validate: compileBuildTimeValidator(schema),
    translate: (_key, fallback) => fallback
  };
  const ConsumerRenderer = () => createElement("output", { "data-consumer-renderer": "ready" }, "Application renderer");
  const markup = renderToStaticMarkup(createElement(OrbyssJsonForms, {
    runtime,
    data: { name: "Ada" },
    renderers: [{ tester: rankWith(1000, uiTypeIs("Control")), renderer: ConsumerRenderer }]
  }));
  assert.match(markup, /data-consumer-renderer="ready"/);
  assert.match(markup, /Application renderer/);
  assert.throws(() => renderToStaticMarkup(createElement(OrbyssJsonForms, {
    runtime,
    data: { name: "Ada" },
    renderers: []
  })), /consumer-supplied JSON Forms renderers/);
});
