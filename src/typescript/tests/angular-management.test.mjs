import assert from "node:assert/strict";
import test from "node:test";
import {
  FormModelerComponentCatalog,
  FormModelerSession
} from "@orbyss/program-kit-forms-modeler";
import {
  ProgramKitFormModelerAngularComponent,
  defaultFormModelerAngularPalette
} from "@orbyss/program-kit-forms-modeler-angular";
import { SchemaModelerSession } from "@orbyss/program-kit-forms-schema-modeler";
import { ProgramKitSchemaModelerAngularComponent } from "@orbyss/program-kit-forms-schema-modeler-angular";
import { LocalizationManagementSession } from "@orbyss/program-kit-localization-management";
import { ProgramKitLocalizationManagementAngularComponent } from "@orbyss/program-kit-localization-management-angular";

function formDocument() {
  return {
    id: "registration", revision: 1, name: "Registration", sourceLocale: "en",
    fields: [{ id: "name", dataPath: "/name", valueKind: "string", required: true, label: { key: "fields.name", defaultText: "Name" } }],
    layout: { id: "registration-layout", kind: "verticalLayout", elements: [{ id: "name-control", kind: "control", fieldId: "name", elements: [] }] },
    actions: []
  };
}

function schemaDocument() {
  return {
    id: "customer", revision: 1, schemaId: "urn:program-kit:schema:customer:1", title: "Customer", rootNodeId: "root",
    nodes: [{ id: "root", parentId: null, propertyName: null, order: 0, valueKind: "object", required: false, additionalProperties: false }]
  };
}

function localizationDocument() {
  return {
    id: "copy", revision: 1, version: "copy-v1", name: "Copy", sourceLocale: "en", state: "draft",
    locales: [{ languageTag: "en", direction: "leftToRight", requiredForPublication: true }, { languageTag: "nl", direction: "leftToRight", fallbackLanguageTag: "en", requiredForPublication: true }],
    messages: [{ key: "fields.name", scope: { kind: "form", resourceId: "registration" }, sourcePattern: "Name", arguments: [], values: [] }]
  };
}

test("Angular schema modeler owns rendering only and mutates the shared governed session", () => {
  const session = new SchemaModelerSession(schemaDocument());
  const component = new ProgramKitSchemaModelerAngularComponent();
  component.session = session;
  component.editorMode = "strictCsp";
  component.ngOnInit();
  assert.equal(typeof ProgramKitSchemaModelerAngularComponent.ɵcmp, "object");
  component.add("string");
  assert.equal(session.snapshot().document.nodes.some(node => node.propertyName === "string1"), true);
  component.setView("graph");
  assert.equal(component.graph().edges.length, 1);
  component.source = '{"type":"object","$ref":"https://example.test/schema"}';
  component.applySource();
  assert.match(component.error, /outside the governed modeler subset/);
});

test("Angular form modeler applies palette and installed-component contracts through the shared session", () => {
  const session = new FormModelerSession(formDocument());
  const component = new ProgramKitFormModelerAngularComponent();
  component.session = session;
  component.editorMode = "strictCsp";
  component.componentCatalog = new FormModelerComponentCatalog([{
    componentId: "ProgramKit.SearchableSelect", contractVersion: "1.0.0", versionRange: "[1.0.0,2.0.0)", displayName: "Searchable select", category: "Choices", supportedValueKinds: ["string"], providerPackage: "@orbyss/program-kit-forms-lookups-angular",
    options: [{ key: "dataSourceId", displayName: "Data source", kind: "string", required: true }]
  }]);
  component.ngOnInit();
  assert.equal(typeof ProgramKitFormModelerAngularComponent.ɵcmp, "object");
  component.add(defaultFormModelerAngularPalette[0]);
  assert.equal(session.snapshot().document.fields.length, 2);
  const field = session.snapshot().document.fields[0];
  component.chooseComponent(field, "ProgramKit.SearchableSelect");
  assert.equal(component.bindingDiagnostics().some(item => item.code === "PKMC005"), true);
  component.updateOption(session.snapshot().document.fields[0], "dataSourceId", "catalog.products");
  assert.deepEqual(component.bindingDiagnostics(), []);
  component.setView("graph");
  assert.equal(component.graph().nodes.length > 0, true);
});

test("Angular localization management applies audited edits and bounded import previews", async () => {
  const session = new LocalizationManagementSession(localizationDocument());
  const component = new ProgramKitLocalizationManagementAngularComponent();
  component.session = session;
  component.actor = { id: "angular-editor", kind: "human" };
  component.capabilities = { edit: true, add: true, import: true, export: true };
  component.pageSize = 20;
  component.ngOnInit();
  assert.equal(typeof ProgramKitLocalizationManagementAngularComponent.ɵcmp, "object");
  const row = component.rows().rows[0];
  component.commitPattern(row, "Naam");
  assert.equal(session.snapshot().document.messages[0].values[0].pattern, "Naam");
  component.addKey = "fields.email";
  component.addScope = "form";
  component.addResource = "registration";
  component.addSource = "Email";
  component.createMessage({ preventDefault() {} });
  assert.equal(session.snapshot().document.messages.length, 2);
  component.importFile = new File(["key,source,nl\nfields.phone,Phone,Telefoon"], "registration.csv", { type: "text/csv" });
  component.importLocale = "nl";
  component.previewImport = async submission => {
    assert.equal(submission.mapping.locale, "nl");
    assert.equal(new TextDecoder().decode(submission.content).includes("Telefoon"), true);
    return { previewId: "angular-preview", contentSha256: "abc", basedOnRevision: 1, mergePolicy: submission.mergePolicy, changes: [], diagnostics: [] };
  };
  await component.submitImport({ preventDefault() {} });
  assert.equal(component.reviewedImport?.previewId, "angular-preview");
});
