import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";
import { defaultRuntimeLimits } from "@orbyss-io/forms-contracts";
import { compileBuildTimeValidator, generateStandaloneValidatorModule } from "@orbyss-io/forms-ajv-build";
import { admitFormRelease, prepareJsonFormsRuntime, createJsonFormsTranslator, createJsonFormsTranslatorAdapter, createPrecompiledJsonFormsAjvFacade } from "@orbyss-io/forms-jsonforms-runtime";
import { FormActionRegistry, RendererRegistry } from "@orbyss-io/forms-renderer-registry";
import { createReferenceDeployment, sha256 } from "./forms-browser/deployment.mjs";

const deployment = await createReferenceDeployment();
const bound = { ...deployment.manifest.validator, validate: compileBuildTimeValidator(deployment.schema) };
const admit = (release = deployment.releaseJson, locales = deployment.localeJson, manifest = deployment.manifest, validator = bound, limits) => admitFormRelease(release, locales, manifest, validator, limits);
const rendererRegistry = new RendererRegistry(["Orbyss.Forms.Wizard", "Orbyss.Forms.ActionBar"].map(componentId => ({ componentId, version: "1.0.0", rank: () => 1, renderer: {} })));
const actionRegistry = new FormActionRegistry({ "synthetic.calculate": async value => value });
const prepare = release => prepareJsonFormsRuntime(release, rendererRegistry, actionRegistry, bound.validate, createJsonFormsTranslator(JSON.parse(deployment.localeJson.en)));

async function standalone(schema) {
  const source = generateStandaloneValidatorModule(schema);
  const output = await build({ stdin: { contents: source, resolveDir: process.cwd() }, bundle: true, write: false, format: "esm", platform: "browser" });
  return (await import("data:text/javascript;base64," + Buffer.from(output.outputFiles[0].text).toString("base64"))).validate;
}

test("published conditional schemas agree across .NET, AJV and standalone modules", async () => {
  let count = 0;
  for (const group of deployment.fixture.cases) {
    const compiled = compileBuildTimeValidator(group.schema);
    const generated = await standalone(group.schema);
    for (const vector of group.vectors) {
      assert.equal(compiled(vector.data).length === 0, vector.valid, `${group.name}: AJV ${JSON.stringify(vector.data)}`);
      assert.equal(generated(vector.data), vector.valid, `${group.name}: standalone ${JSON.stringify(vector.data)}`);
      count++;
    }
  }
  assert(count >= 500);
});

test("published release admission binds the complete release and four locale artifacts", async () => {
  const admitted = await admit();
  assert.equal(admitted.release.id.value, "synthetic-product-v1");
  assert.deepEqual(Object.keys(admitted.translations), ["en", "nl", "de", "ar"]);
  assert.throws(() => { admitted.release.candidate.fields[0].required = false; }, TypeError);
  assert.throws(() => { admitted.translations.en["fields.name"] = "changed"; }, TypeError);
  const prepared = await prepare(admitted.release);
  assert.throws(() => { prepared.schema.properties.name.type = "number"; }, TypeError);
  assert.equal(prepared.validate({ name: "Ada", kind: "standard", quantity: 1 }).length, 0);
  assert(prepared.validate({ name: "Ada", kind: "custom", quantity: 1 }).length > 0);
  assert.equal(prepared.validate({ name: "Ada", kind: "custom", detail: "yes", quantity: 1 }).length, 0);
  for (const quantity of [1e30, -1e30, 100.0001])
    assert(prepared.validate({ name: "Ada", kind: "standard", quantity }).some(issue => issue.path === "/quantity"));
});

test("JSON Forms label probes resolve the manifest's base translation key", () => {
  const translate = createJsonFormsTranslatorAdapter(createJsonFormsTranslator({ "field": "Translated", "override.label": "Explicit" }));
  assert.equal(translate("field.label", "Fallback"), "Translated");
  assert.equal(translate("override.label", "Fallback"), "Explicit");
  assert.equal(translate("unknown.error.required"), undefined);
  assert.equal(translate("unknown.label", "Fallback"), "Fallback");
});

test("admission snapshots its trust inputs before awaiting verification", async () => {
  const expected = structuredClone(deployment.manifest);
  const locales = { ...deployment.localeJson };
  const validator = { ...bound };
  const limits = { ...defaultRuntimeLimits };
  const pending = admit(deployment.releaseJson, locales, expected, validator, limits);
  limits.maximumArtifactBytes = 1;
  expected.retired = true; locales.en = "{}"; validator.validate = () => { throw new Error("mutated"); };
  const result = await pending;
  assert(result.validate({}).length > 0);
  assert.equal(result.translations.en["fields.name"], "Name");
});

test("foreign, retired, tampered and mixed artifacts fail before rendering", async () => {
  for (const mutate of [
    r => { r.id.value = "foreign"; }, r => { r.candidate.formId.value = "foreign"; }, r => { r.candidate.revision.value++; },
    r => { r.retired = true; }, r => { r.candidate.fields[0].required = false; },
    r => { r.candidate.actions[0].handlerId = "foreign"; }, r => { r.candidate.renderers[0].componentId = "foreign"; },
    r => { r.candidate.dataSchema.content += " "; r.candidate.dataSchema.sha256 = sha256(r.candidate.dataSchema.content); }
  ]) {
    const release = JSON.parse(deployment.releaseJson); mutate(release);
    await assert.rejects(admit(JSON.stringify(release)), /digest/);
  }
  for (const patch of [{ formId: "foreign" }, { releaseId: "foreign" }, { revision: 2 }, { retired: true }])
    await assert.rejects(admit(deployment.releaseJson, deployment.localeJson, { ...deployment.manifest, ...patch }));
  await assert.rejects(admit(deployment.releaseJson, { ...deployment.localeJson, en: "{}" }), /digest/);
  await assert.rejects(admit(deployment.releaseJson, deployment.localeJson, deployment.manifest, { ...bound, sha256: "0".repeat(64) }), /validator/);
  await assert.rejects(admit(deployment.releaseJson, deployment.localeJson, deployment.manifest, { ...bound, schemaSha256: "0".repeat(64) }), /validator/);
  await assert.rejects(admit("null"));
  await assert.rejects(admit("{"));
  await assert.rejects(admit(deployment.releaseJson, deployment.localeJson, deployment.manifest, bound, { maximumArtifactBytes: 10, maximumJsonNodes: 10, maximumJsonDepth: 2 }), /limit/);
});

test("trusted malformed artifacts still fail shape and locale completeness checks", async () => {
  const release = JSON.parse(deployment.releaseJson); delete release.candidate.fields;
  const content = JSON.stringify(release);
  await assert.rejects(admit(content, deployment.localeJson, { ...deployment.manifest, releaseSha256: sha256(content) }), /fields/);
  const en = JSON.parse(deployment.localeJson.en); delete en["fields.name"];
  const english = JSON.stringify(en);
  await assert.rejects(admit(deployment.releaseJson, { ...deployment.localeJson, en: english }, { ...deployment.manifest, locales: { ...deployment.manifest.locales, en: sha256(english) } }), /translation/);
});

test("preparation rejects undeclared renderers, handlers, unsafe UI and external rule references", async () => {
  const admitted = await admit();
  await assert.rejects(prepareJsonFormsRuntime(admitted.release, new RendererRegistry([]), actionRegistry, bound.validate, () => ""), /renderer/);
  await assert.rejects(prepareJsonFormsRuntime(admitted.release, rendererRegistry, new FormActionRegistry({}), bound.validate, () => ""), /handler/);
  const prepared = await prepare(admitted.release);
  await assert.rejects(prepared.dispatchAction("unknown", {}, { signal: new AbortController().signal }), /not declared/);
  for (const ui of [{ type: "UnknownWithoutId" }, { type: "Control", script: "alert(1)" }, { type: "Control", rule: { effect: "SHOW", condition: { scope: "#", schema: { $ref: "https://example.invalid/schema" } } } }]) {
    const release = structuredClone(admitted.release);
    const content = JSON.stringify(ui); release.candidate.uiSchema = { content, sha256: sha256(content), mediaType: "application/json" };
    await assert.rejects(prepare(release), /allowlist|forbidden|External/);
  }
});

test("compiler composition preserves visibility, enablement and explicit read-only", async () => {
  const admitted = await admit();
  const prepared = await prepare(admitted.release);
  const wrapper = prepared.uiSchema.elements[0].elements[3].elements[0];
  assert.equal(wrapper.type, "VerticalLayout");
  assert.equal(wrapper.rule.effect, "SHOW");
  assert.equal(wrapper.elements[0].rule.effect, "ENABLE");
  const facade = createPrecompiledJsonFormsAjvFacade(prepared.schema, prepared.validate);
  assert.equal(facade.compile(wrapper.rule.condition.schema)({ kind: "standard" }), false);
  assert.equal(facade.compile(wrapper.rule.condition.schema)({ kind: "custom" }), true);
  assert.equal(facade.compile(wrapper.elements[0].rule.condition.schema)({ kind: "custom", editable: false }), false);
  assert.equal(facade.compile(wrapper.elements[0].rule.condition.schema)({ kind: "custom", editable: true }), true);
  assert.equal(prepared.schema.properties.reference.readOnly, true);
  assert.equal(prepared.uiSchema.elements[1].elements[1].rule, undefined, "An enable rule must not override authored read-only");
});
