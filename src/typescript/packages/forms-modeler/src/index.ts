export type ModelerValueKind = "string" | "integer" | "number" | "boolean" | "date" | "dateTime" | "time" | "object" | "array";
export type ModelerElementKind = "control" | "group" | "horizontalLayout" | "verticalLayout" | "wizard" | "step" | "text" | "actionBar";
export type ModelerActionKind = "back" | "next" | "saveDraft" | "skip" | "cancel" | "submit" | "custom";
export type ModelerConditionOperator = "equals" | "notEquals" | "isPresent" | "isAbsent";

export interface ModelerLocalizedText {
  readonly key: string;
  readonly defaultText: string;
  readonly context?: string | null;
}

export interface ModelerIconReference {
  readonly name: string;
  readonly bundle?: string | null;
}

export interface ModelerChoice {
  readonly value: string;
  readonly label: ModelerLocalizedText;
}

export interface ModelerConstraints {
  readonly minimum?: number | null;
  readonly maximum?: number | null;
  readonly minimumLength?: number | null;
  readonly maximumLength?: number | null;
  readonly minimumItems?: number | null;
  readonly maximumItems?: number | null;
  readonly pattern?: string | null;
  readonly choices?: readonly ModelerChoice[] | null;
}

export interface ModelerComponentReference {
  readonly componentId: string;
  readonly versionRange: string;
  readonly options?: Readonly<Record<string, string>> | null;
}

export type FormModelerComponentOptionKind = "string" | "boolean" | "integer" | "choice";

export interface FormModelerComponentOptionContract {
  readonly key: string;
  readonly displayName: string;
  readonly kind: FormModelerComponentOptionKind;
  readonly required: boolean;
  readonly defaultValue?: string;
  readonly choices?: readonly { readonly value: string; readonly label: string }[];
}

/** Trusted authoring metadata supplied by an installed renderer feature package. */
export interface FormModelerComponentContract {
  readonly componentId: string;
  readonly contractVersion: string;
  readonly versionRange: string;
  readonly displayName: string;
  readonly description?: string;
  readonly category: string;
  readonly supportedValueKinds: readonly ModelerValueKind[];
  readonly providerPackage?: string;
  readonly options?: readonly FormModelerComponentOptionContract[];
}

export class FormModelerComponentCatalog {
  readonly #contracts: readonly FormModelerComponentContract[];

  public constructor(contracts: readonly FormModelerComponentContract[]) {
    const componentIds = new Set<string>();
    for (const contract of contracts) {
      requireIdentifier(contract.componentId, "componentId");
      if (componentIds.has(contract.componentId)) throw new Error(`Duplicate component contract '${contract.componentId}'.`);
      if (!/^\d+\.\d+\.\d+$/.test(contract.contractVersion)) throw new Error(`Component contract '${contract.componentId}' requires a semantic contract version.`);
      if (contract.versionRange.trim().length === 0) throw new Error(`Component contract '${contract.componentId}' requires a compatible version range.`);
      if (contract.displayName.trim().length === 0 || contract.category.trim().length === 0) throw new Error(`Component contract '${contract.componentId}' requires display and category names.`);
      if (contract.supportedValueKinds.length === 0 || contract.supportedValueKinds.some(kind => !modelerValueKinds.has(kind))) throw new Error(`Component contract '${contract.componentId}' has invalid supported value kinds.`);
      const optionKeys = new Set<string>();
      for (const option of contract.options ?? []) {
        requireIdentifier(option.key, "component option key");
        if (optionKeys.has(option.key)) throw new Error(`Component contract '${contract.componentId}' repeats option '${option.key}'.`);
        if (option.displayName.trim().length === 0) throw new Error(`Component option '${option.key}' requires a display name.`);
        if (!componentOptionKinds.has(option.kind)) throw new Error(`Component option '${option.key}' has an invalid kind.`);
        if (option.kind === "choice" && (option.choices === undefined || option.choices.length === 0)) throw new Error(`Choice option '${option.key}' requires choices.`);
        if (option.kind !== "choice" && option.choices !== undefined) throw new Error(`Only choice option '${option.key}' may declare choices.`);
        const values = new Set<string>();
        for (const choice of option.choices ?? []) {
          if (choice.value.length === 0 || choice.label.trim().length === 0 || values.has(choice.value)) throw new Error(`Choice option '${option.key}' has invalid or duplicate values.`);
          values.add(choice.value);
        }
        if (option.defaultValue !== undefined && !validComponentOptionValue(option, option.defaultValue)) throw new Error(`Component option '${option.key}' has an invalid default value.`);
        optionKeys.add(option.key);
      }
      componentIds.add(contract.componentId);
    }
    this.#contracts = deepFreeze(JSON.parse(JSON.stringify(contracts)) as FormModelerComponentContract[]);
  }

  public list(): readonly FormModelerComponentContract[] { return this.#contracts; }

  public listFor(valueKind: ModelerValueKind): readonly FormModelerComponentContract[] {
    return this.#contracts.filter(contract => contract.supportedValueKinds.includes(valueKind));
  }

  public resolve(componentId: string): FormModelerComponentContract | undefined {
    return this.#contracts.find(contract => contract.componentId === componentId);
  }

  public createReference(componentId: string): ModelerComponentReference {
    const contract = this.resolve(componentId);
    if (contract === undefined) throw new Error(`Component '${componentId}' is not installed.`);
    const options = Object.fromEntries((contract.options ?? []).flatMap(option => option.defaultValue === undefined ? [] : [[option.key, option.defaultValue]]));
    return Object.freeze({ componentId, versionRange: contract.versionRange, ...(Object.keys(options).length === 0 ? {} : { options: Object.freeze(options) }) });
  }

  public validateBindings(fields: readonly FormModelerField[]): readonly FormModelerDiagnostic[] {
    const diagnostics: FormModelerDiagnostic[] = [];
    fields.forEach((field, index) => {
      if (field.component === undefined || field.component === null) return;
      const path = `/fields/${index}/component`;
      const contract = this.resolve(field.component.componentId);
      if (contract === undefined) {
        diagnostics.push({ code: "PKMC001", path: `${path}/componentId`, message: `Component '${field.component.componentId}' is not installed.` });
        return;
      }
      if (!contract.supportedValueKinds.includes(field.valueKind)) diagnostics.push({ code: "PKMC002", path: `${path}/componentId`, message: `Component '${contract.componentId}' does not support '${field.valueKind}'.` });
      if (field.component.versionRange !== contract.versionRange) diagnostics.push({ code: "PKMC003", path: `${path}/versionRange`, message: `Component '${contract.componentId}' must use its declared compatible version range.` });
      const values = field.component.options ?? {};
      const declared = new Map((contract.options ?? []).map(option => [option.key, option]));
      for (const key of Object.keys(values)) if (!declared.has(key)) diagnostics.push({ code: "PKMC004", path: `${path}/options/${escapePointer(key)}`, message: `Option '${key}' is not declared by the component package.` });
      for (const option of contract.options ?? []) {
        const value = values[option.key];
        if (option.required && (value === undefined || value.length === 0)) diagnostics.push({ code: "PKMC005", path: `${path}/options/${escapePointer(option.key)}`, message: `Option '${option.key}' is required.` });
        else if (value !== undefined && !validComponentOptionValue(option, value)) diagnostics.push({ code: "PKMC006", path: `${path}/options/${escapePointer(option.key)}`, message: `Option '${option.key}' has an invalid value.` });
      }
    });
    return Object.freeze(diagnostics.map(item => Object.freeze(item)));
  }
}

export interface FormModelerField {
  readonly id: string;
  readonly dataPath: string;
  readonly valueKind: ModelerValueKind;
  readonly required: boolean;
  readonly label: ModelerLocalizedText;
  readonly description?: ModelerLocalizedText | null;
  readonly constraints?: ModelerConstraints | null;
  readonly component?: ModelerComponentReference | null;
}

export interface ModelerVisibilityCondition {
  readonly fieldId: string;
  readonly operator: ModelerConditionOperator;
  readonly value?: string | null;
}

export interface ModelerWizardOptions {
  readonly navigationPolicy: "linear" | "nonLinear" | "visited";
  readonly navigationPlacement: "top" | "side" | "adaptive";
  readonly progressStyle: "line" | "segmented" | "progress";
  readonly validateBeforeAdvance: boolean;
  readonly saveProgress: boolean;
  readonly deepLink: boolean;
}

export interface FormModelerElement {
  readonly id: string;
  readonly kind: ModelerElementKind;
  readonly elements: readonly FormModelerElement[];
  readonly fieldId?: string | null;
  readonly text?: ModelerLocalizedText | null;
  readonly icon?: ModelerIconReference | null;
  readonly visibility?: ModelerVisibilityCondition | null;
  readonly wizard?: ModelerWizardOptions | null;
  readonly presentation?: Readonly<Record<string, string>> | null;
  readonly actionIds?: readonly string[] | null;
}

export interface FormModelerAction {
  readonly id: string;
  readonly kind: ModelerActionKind;
  readonly label: ModelerLocalizedText;
  readonly handlerId: string;
  readonly requiresValidForm: boolean;
  readonly icon?: ModelerIconReference | null;
}

/** Trusted metadata exported by an installed reusable feature package or the application itself. */
export interface FormModelerActionContract {
  readonly handlerId: string;
  readonly contractVersion: string;
  readonly displayName: string;
  readonly description?: string;
  readonly execution: "client" | "server" | "hybrid";
  readonly supportedKinds: readonly ModelerActionKind[];
  readonly providerPackage?: string;
  readonly requiredPermissions?: readonly string[];
}

export class FormModelerActionCatalog {
  readonly #contracts: readonly FormModelerActionContract[];

  public constructor(contracts: readonly FormModelerActionContract[]) {
    const ids = new Set<string>();
    for (const contract of contracts) {
      requireIdentifier(contract.handlerId, "handlerId");
      if (ids.has(contract.handlerId)) throw new Error(`Duplicate action contract '${contract.handlerId}'.`);
      if (!/^\d+\.\d+\.\d+$/.test(contract.contractVersion)) throw new Error(`Action contract '${contract.handlerId}' requires a semantic contract version.`);
      if (contract.displayName.trim().length === 0) throw new Error(`Action contract '${contract.handlerId}' requires a display name.`);
      if (contract.supportedKinds.length === 0 || contract.supportedKinds.some(kind => !modelerActionKinds.has(kind))) throw new Error(`Action contract '${contract.handlerId}' has invalid supported kinds.`);
      ids.add(contract.handlerId);
    }
    this.#contracts = deepFreeze(JSON.parse(JSON.stringify(contracts)) as FormModelerActionContract[]);
  }

  public list(): readonly FormModelerActionContract[] { return this.#contracts; }

  public resolve(handlerId: string): FormModelerActionContract | undefined {
    return this.#contracts.find(contract => contract.handlerId === handlerId);
  }

  public validateBindings(actions: readonly FormModelerAction[]): readonly FormModelerDiagnostic[] {
    const diagnostics: FormModelerDiagnostic[] = [];
    actions.forEach((action, index) => {
      const contract = this.resolve(action.handlerId);
      if (contract === undefined) {
        diagnostics.push({ code: "PKM090", path: `/actions/${index}/handlerId`, message: `Handler '${action.handlerId}' is not installed.` });
      } else if (!contract.supportedKinds.includes(action.kind)) {
        diagnostics.push({ code: "PKM091", path: `/actions/${index}/kind`, message: `Handler '${action.handlerId}' does not support '${action.kind}'.` });
      }
    });
    return Object.freeze(diagnostics.map(item => Object.freeze(item)));
  }
}

export interface FormModelerDocument {
  readonly id: string;
  readonly revision: number;
  readonly name: string;
  readonly sourceLocale: string;
  readonly fields: readonly FormModelerField[];
  readonly layout: FormModelerElement;
  readonly actions: readonly FormModelerAction[];
  readonly metadata?: Readonly<Record<string, string>> | null;
}

export interface FormModelerDiagnostic {
  readonly code: string;
  readonly path: string;
  readonly message: string;
}

export interface FormModelerLimits {
  readonly maximumFields: number;
  readonly maximumActions: number;
  readonly maximumElements: number;
  readonly maximumDepth: number;
  readonly maximumStringLength: number;
  readonly maximumSourceBytes: number;
  readonly maximumHistory: number;
  readonly maximumRememberedCommands: number;
}

export const defaultFormModelerLimits: FormModelerLimits = Object.freeze({
  maximumFields: 500,
  maximumActions: 100,
  maximumElements: 2_000,
  maximumDepth: 32,
  maximumStringLength: 4_096,
  maximumSourceBytes: 1_048_576,
  maximumHistory: 100,
  maximumRememberedCommands: 1_000
});

export type FormModelerOperation =
  | { readonly type: "replaceDocument"; readonly document: FormModelerDocument }
  | { readonly type: "upsertField"; readonly field: FormModelerField }
  | { readonly type: "removeField"; readonly fieldId: string }
  | { readonly type: "upsertAction"; readonly action: FormModelerAction }
  | { readonly type: "removeAction"; readonly actionId: string }
  | { readonly type: "insertElement"; readonly parentId: string; readonly index: number; readonly element: FormModelerElement }
  | { readonly type: "replaceElement"; readonly elementId: string; readonly element: FormModelerElement }
  | { readonly type: "removeElement"; readonly elementId: string }
  | { readonly type: "moveElement"; readonly elementId: string; readonly parentId: string; readonly index: number };

export interface FormModelerCommand {
  readonly commandId: string;
  readonly expectedSequence: number;
  readonly operations: readonly FormModelerOperation[];
}

export interface FormModelerSnapshot {
  readonly document: FormModelerDocument;
  readonly sequence: number;
  readonly selectedId?: string;
  readonly canUndo: boolean;
  readonly canRedo: boolean;
}

export class FormModelerValidationError extends Error {
  public constructor(public readonly diagnostics: readonly FormModelerDiagnostic[]) {
    super(diagnostics.map(item => `${item.code} ${item.path}: ${item.message}`).join("\n"));
    this.name = "FormModelerValidationError";
  }
}

export class FormModelerConcurrencyError extends Error {
  public constructor(public readonly expected: number, public readonly actual: number) {
    super(`The modeler command expected sequence ${expected}, but the current sequence is ${actual}.`);
    this.name = "FormModelerConcurrencyError";
  }
}

export class FormModelerSession {
  readonly #limits: FormModelerLimits;
  #document: FormModelerDocument;
  #sequence = 0;
  #selectedId: string | undefined;
  #undo: FormModelerDocument[] = [];
  #redo: FormModelerDocument[] = [];
  readonly #commands = new Map<string, string>();
  readonly #commandOrder: string[] = [];

  public constructor(document: FormModelerDocument, limits: Partial<FormModelerLimits> = {}) {
    this.#limits = Object.freeze({ ...defaultFormModelerLimits, ...limits });
    assertValidLimits(this.#limits);
    this.#document = validatedSnapshot(document, this.#limits);
  }

  public snapshot(): FormModelerSnapshot {
    return Object.freeze({
      document: this.#document,
      sequence: this.#sequence,
      ...(this.#selectedId === undefined ? {} : { selectedId: this.#selectedId }),
      canUndo: this.#undo.length > 0,
      canRedo: this.#redo.length > 0
    });
  }

  public select(id?: string): FormModelerSnapshot {
    if (id !== undefined && !documentContainsId(this.#document, id)) throw new Error(`Modeler selection '${id}' does not exist.`);
    this.#selectedId = id;
    return this.snapshot();
  }

  public apply(command: FormModelerCommand): FormModelerSnapshot {
    requireIdentifier(command.commandId, "commandId");
    const fingerprint = JSON.stringify(command.operations);
    const previousFingerprint = this.#commands.get(command.commandId);
    if (previousFingerprint !== undefined) {
      if (previousFingerprint !== fingerprint) throw new Error(`Command ID '${command.commandId}' was reused with different operations.`);
      return this.snapshot();
    }
    if (command.expectedSequence !== this.#sequence) {
      throw new FormModelerConcurrencyError(command.expectedSequence, this.#sequence);
    }
    if (command.operations.length === 0) throw new Error("A modeler command requires at least one operation.");
    let next = this.#document;
    for (const operation of command.operations) next = applyOperation(next, operation);
    next = validatedSnapshot(next, this.#limits);
    this.#undo.push(this.#document);
    if (this.#undo.length > this.#limits.maximumHistory) this.#undo.shift();
    this.#document = next;
    this.#redo = [];
    this.#sequence += 1;
    this.#remember(command.commandId, fingerprint);
    if (this.#selectedId !== undefined && !documentContainsId(next, this.#selectedId)) this.#selectedId = undefined;
    return this.snapshot();
  }

  public undo(): FormModelerSnapshot {
    const previous = this.#undo.pop();
    if (previous === undefined) return this.snapshot();
    this.#redo.push(this.#document);
    this.#document = previous;
    this.#sequence += 1;
    if (this.#selectedId !== undefined && !documentContainsId(previous, this.#selectedId)) this.#selectedId = undefined;
    return this.snapshot();
  }

  public redo(): FormModelerSnapshot {
    const next = this.#redo.pop();
    if (next === undefined) return this.snapshot();
    this.#undo.push(this.#document);
    this.#document = next;
    this.#sequence += 1;
    if (this.#selectedId !== undefined && !documentContainsId(next, this.#selectedId)) this.#selectedId = undefined;
    return this.snapshot();
  }

  #remember(commandId: string, fingerprint: string): void {
    this.#commands.set(commandId, fingerprint);
    this.#commandOrder.push(commandId);
    if (this.#commandOrder.length > this.#limits.maximumRememberedCommands) {
      const forgotten = this.#commandOrder.shift();
      if (forgotten !== undefined) this.#commands.delete(forgotten);
    }
  }
}

export function validateFormModelerDocument(
  document: FormModelerDocument,
  limits: FormModelerLimits = defaultFormModelerLimits
): readonly FormModelerDiagnostic[] {
  const diagnostics: FormModelerDiagnostic[] = [];
  const add = (code: string, path: string, message: string) => diagnostics.push({ code, path, message });
  inspectJsonValue(document, limits, add);
  if (!hasDocumentShape(document)) {
    add("PKM000", "/", "Document does not match the provider-neutral modeler contract.");
    return Object.freeze(diagnostics.map(item => Object.freeze(item)));
  }
  if (!validIdentifier(document.id)) add("PKM001", "/id", "Form ID must be a portable identifier.");
  if (!Number.isSafeInteger(document.revision) || document.revision < 1) add("PKM002", "/revision", "Revision must be a positive safe integer.");
  if (document.name.trim().length === 0) add("PKM003", "/name", "Name is required.");
  if (!validLocale(document.sourceLocale)) add("PKM004", "/sourceLocale", "Source locale must be a BCP 47-style tag.");
  if (document.fields.length > limits.maximumFields) add("PKM005", "/fields", "Field limit exceeded.");
  if (document.actions.length > limits.maximumActions) add("PKM006", "/actions", "Action limit exceeded.");

  const fieldIds = uniqueIds(document.fields, "/fields", add);
  const paths = new Set<string>();
  document.fields.forEach((field, index) => {
    const path = `/fields/${index}`;
    if (!validJsonPointer(field.dataPath)) add("PKM010", `${path}/dataPath`, "Data path must be a rooted RFC 6901 JSON Pointer.");
    if (!modelerValueKinds.has(field.valueKind)) add("PKM014", `${path}/valueKind`, "Value kind is not supported.");
    if (paths.has(field.dataPath)) add("PKM011", `${path}/dataPath`, "Data path is duplicated.");
    paths.add(field.dataPath);
    validateText(field.label, `${path}/label`, add);
    if (field.description !== undefined && field.description !== null) validateText(field.description, `${path}/description`, add);
    validateConstraints(field, path, add);
    if (field.component !== undefined && field.component !== null) {
      if (!validIdentifier(field.component.componentId)) add("PKM012", `${path}/component/componentId`, "Component ID must be portable.");
      if (field.component.versionRange.trim().length === 0) add("PKM013", `${path}/component/versionRange`, "Component version range is required.");
    }
  });

  const actionIds = uniqueIds(document.actions, "/actions", add);
  document.actions.forEach((action, index) => {
    const path = `/actions/${index}`;
    validateText(action.label, `${path}/label`, add);
    if (!modelerActionKinds.has(action.kind)) add("PKM021", `${path}/kind`, "Action kind is not supported.");
    if (!validIdentifier(action.handlerId)) add("PKM020", `${path}/handlerId`, "Handler ID must be portable.");
    if (action.icon !== undefined && action.icon !== null) validateIcon(action.icon, `${path}/icon`, add);
  });

  const elementIds = new Set<string>();
  let elementCount = 0;
  const visit = (element: FormModelerElement, path: string, depth: number) => {
    elementCount += 1;
    if (depth > limits.maximumDepth) add("PKM030", path, "Layout depth limit exceeded.");
    if (!validIdentifier(element.id)) add("PKM031", `${path}/id`, "Element ID must be portable.");
    if (elementIds.has(element.id)) add("PKM032", `${path}/id`, "Element ID is duplicated.");
    elementIds.add(element.id);
    if (!modelerElementKinds.has(element.kind)) add("PKM043", `${path}/kind`, "Element kind is not supported.");
    if (element.kind === "control") {
      if (element.fieldId === undefined || element.fieldId === null || !fieldIds.has(element.fieldId)) add("PKM033", `${path}/fieldId`, "Control must reference an existing field.");
    } else if (element.fieldId !== undefined && element.fieldId !== null) add("PKM034", `${path}/fieldId`, "Only controls may reference a field.");
    if (element.kind === "actionBar") {
      if (element.actionIds === undefined || element.actionIds === null || element.actionIds.length === 0) add("PKM035", `${path}/actionIds`, "Action bar requires actions.");
      const seen = new Set<string>();
      for (const actionId of element.actionIds ?? []) {
        if (seen.has(actionId)) add("PKM036", `${path}/actionIds`, `Action '${actionId}' is repeated.`);
        if (!actionIds.has(actionId)) add("PKM037", `${path}/actionIds`, `Action '${actionId}' does not exist.`);
        seen.add(actionId);
      }
    } else if (element.actionIds !== undefined && element.actionIds !== null) add("PKM038", `${path}/actionIds`, "Only action bars may reference actions.");
    if (element.kind === "wizard" && element.wizard === undefined) add("PKM039", `${path}/wizard`, "Wizard options are required.");
    if (element.kind !== "wizard" && element.wizard !== undefined && element.wizard !== null) add("PKM040", `${path}/wizard`, "Only wizard elements accept wizard options.");
    if (element.visibility !== undefined && element.visibility !== null && !fieldIds.has(element.visibility.fieldId)) add("PKM041", `${path}/visibility/fieldId`, "Visibility condition references an unknown field.");
    if (element.text !== undefined && element.text !== null) validateText(element.text, `${path}/text`, add);
    if (element.icon !== undefined && element.icon !== null) validateIcon(element.icon, `${path}/icon`, add);
    element.elements.forEach((child, index) => visit(child, `${path}/elements/${index}`, depth + 1));
  };
  visit(document.layout, "/layout", 1);
  if (elementCount > limits.maximumElements) add("PKM042", "/layout", "Element limit exceeded.");
  return Object.freeze(diagnostics.map(item => Object.freeze(item)));
}

export function parseFormModelerDocument(source: string, limits: FormModelerLimits = defaultFormModelerLimits): FormModelerDocument {
  if (new TextEncoder().encode(source).byteLength > limits.maximumSourceBytes) throw new Error("The modeler source exceeds the configured byte limit.");
  const value: unknown = JSON.parse(source);
  if (!isRecord(value)) throw new Error("The modeler document root must be an object.");
  return validatedSnapshot(value as unknown as FormModelerDocument, limits);
}

export function serializeFormModelerDocument(document: FormModelerDocument): string {
  return JSON.stringify(validatedSnapshot(document, defaultFormModelerLimits), null, 2) + "\n";
}

export interface FormModelerGraphNode { readonly id: string; readonly kind: "form" | "field" | "element" | "action"; readonly label: string; }
export interface FormModelerGraphEdge { readonly from: string; readonly to: string; readonly kind: "contains" | "binds" | "controls-visibility" | "invokes"; }
export interface FormModelerGraph { readonly nodes: readonly FormModelerGraphNode[]; readonly edges: readonly FormModelerGraphEdge[]; }

export function projectFormModelerGraph(document: FormModelerDocument): FormModelerGraph {
  const valid = validatedSnapshot(document, defaultFormModelerLimits);
  const nodes: FormModelerGraphNode[] = [{ id: `form:${valid.id}`, kind: "form", label: valid.name }];
  const edges: FormModelerGraphEdge[] = [];
  for (const field of valid.fields) {
    nodes.push({ id: `field:${field.id}`, kind: "field", label: field.label.defaultText });
    edges.push({ from: `form:${valid.id}`, to: `field:${field.id}`, kind: "contains" });
  }
  for (const action of valid.actions) {
    nodes.push({ id: `action:${action.id}`, kind: "action", label: action.label.defaultText });
    edges.push({ from: `form:${valid.id}`, to: `action:${action.id}`, kind: "contains" });
  }
  const visit = (element: FormModelerElement, parent: string) => {
    const id = `element:${element.id}`;
    nodes.push({ id, kind: "element", label: element.text?.defaultText ?? element.id });
    edges.push({ from: parent, to: id, kind: "contains" });
    if (element.fieldId !== undefined && element.fieldId !== null) edges.push({ from: id, to: `field:${element.fieldId}`, kind: "binds" });
    if (element.visibility !== undefined && element.visibility !== null) edges.push({ from: id, to: `field:${element.visibility.fieldId}`, kind: "controls-visibility" });
    for (const actionId of element.actionIds ?? []) edges.push({ from: id, to: `action:${actionId}`, kind: "invokes" });
    for (const child of element.elements) visit(child, id);
  };
  visit(valid.layout, `form:${valid.id}`);
  return Object.freeze({ nodes: Object.freeze(nodes.map(item => Object.freeze(item))), edges: Object.freeze(edges.map(item => Object.freeze(item))) });
}

function applyOperation(document: FormModelerDocument, operation: FormModelerOperation): FormModelerDocument {
  switch (operation.type) {
    case "replaceDocument": return operation.document;
    case "upsertField": return { ...document, fields: upsert(document.fields, operation.field) };
    case "removeField": {
      if (!document.fields.some(item => item.id === operation.fieldId)) throw new Error(`Field '${operation.fieldId}' does not exist.`);
      return { ...document, fields: document.fields.filter(item => item.id !== operation.fieldId) };
    }
    case "upsertAction": return { ...document, actions: upsert(document.actions, operation.action) };
    case "removeAction": {
      if (!document.actions.some(item => item.id === operation.actionId)) throw new Error(`Action '${operation.actionId}' does not exist.`);
      return { ...document, actions: document.actions.filter(item => item.id !== operation.actionId) };
    }
    case "insertElement": return { ...document, layout: insertElement(document.layout, operation.parentId, operation.index, operation.element) };
    case "replaceElement": {
      if (document.layout.id === operation.elementId) return { ...document, layout: operation.element };
      if (findElement(document.layout, operation.elementId) === undefined) throw new Error(`Element '${operation.elementId}' does not exist.`);
      return { ...document, layout: mapElement(document.layout, operation.elementId, () => operation.element) };
    }
    case "removeElement": {
      if (document.layout.id === operation.elementId) throw new Error("The root layout element cannot be removed.");
      if (findElement(document.layout, operation.elementId) === undefined) throw new Error(`Element '${operation.elementId}' does not exist.`);
      return { ...document, layout: removeElement(document.layout, operation.elementId) };
    }
    case "moveElement": {
      if (document.layout.id === operation.elementId) throw new Error("The root layout element cannot be moved.");
      const moving = findElement(document.layout, operation.elementId);
      if (moving === undefined) throw new Error(`Element '${operation.elementId}' does not exist.`);
      if (findElement(moving, operation.parentId) !== undefined) throw new Error("An element cannot be moved into itself or one of its descendants.");
      const removed = removeElement(document.layout, operation.elementId);
      return { ...document, layout: insertElement(removed, operation.parentId, operation.index, moving) };
    }
  }
}

function upsert<T extends { readonly id: string }>(items: readonly T[], item: T): readonly T[] {
  const index = items.findIndex(candidate => candidate.id === item.id);
  return index < 0 ? [...items, item] : items.map((candidate, position) => position === index ? item : candidate);
}

function insertElement(root: FormModelerElement, parentId: string, index: number, element: FormModelerElement): FormModelerElement {
  if (!Number.isSafeInteger(index) || index < 0) throw new Error("Element insertion index must be a nonnegative safe integer.");
  let found = false;
  const result = mapElement(root, parentId, parent => {
    found = true;
    const insertion = Math.min(index, parent.elements.length);
    return { ...parent, elements: [...parent.elements.slice(0, insertion), element, ...parent.elements.slice(insertion)] };
  });
  if (!found) throw new Error(`Element parent '${parentId}' does not exist.`);
  return result;
}

function mapElement(root: FormModelerElement, id: string, replace: (element: FormModelerElement) => FormModelerElement): FormModelerElement {
  if (root.id === id) return replace(root);
  return { ...root, elements: root.elements.map(child => mapElement(child, id, replace)) };
}

function removeElement(root: FormModelerElement, id: string): FormModelerElement {
  return { ...root, elements: root.elements.filter(child => child.id !== id).map(child => removeElement(child, id)) };
}

function findElement(root: FormModelerElement, id: string): FormModelerElement | undefined {
  if (root.id === id) return root;
  for (const child of root.elements) {
    const match = findElement(child, id);
    if (match !== undefined) return match;
  }
  return undefined;
}

function validatedSnapshot(document: FormModelerDocument, limits: FormModelerLimits): FormModelerDocument {
  const clone = JSON.parse(JSON.stringify(document)) as FormModelerDocument;
  const diagnostics = validateFormModelerDocument(clone, limits);
  if (diagnostics.length > 0) throw new FormModelerValidationError(diagnostics);
  return deepFreeze(clone);
}

function validateConstraints(field: FormModelerField, path: string, add: (code: string, path: string, message: string) => void): void {
  const constraints = field.constraints;
  if (constraints === undefined || constraints === null) return;
  if (constraints.minimum !== undefined && constraints.minimum !== null && constraints.maximum !== undefined && constraints.maximum !== null && constraints.minimum > constraints.maximum) add("PKM050", `${path}/constraints`, "Minimum cannot exceed maximum.");
  if (constraints.minimumLength !== undefined && constraints.minimumLength !== null && !["string"].includes(field.valueKind)) add("PKM051", `${path}/constraints/minimumLength`, "Text length applies only to strings.");
  if (constraints.minimumItems !== undefined && constraints.minimumItems !== null && field.valueKind !== "array") add("PKM052", `${path}/constraints/minimumItems`, "Item count applies only to arrays.");
  if (constraints.pattern !== undefined && constraints.pattern !== null && field.valueKind !== "string") add("PKM053", `${path}/constraints/pattern`, "Pattern applies only to strings.");
  for (const [name, value] of Object.entries(constraints)) {
    if ((name.startsWith("minimum") || name.startsWith("maximum")) && typeof value === "number" && (!Number.isFinite(value) || value < 0 && name.endsWith("Length"))) add("PKM054", `${path}/constraints/${name}`, "Constraint value is outside the portable range.");
  }
}

function inspectJsonValue(value: unknown, limits: FormModelerLimits, add: (code: string, path: string, message: string) => void, path = "", depth = 0): void {
  if (depth > limits.maximumDepth + 8) { add("PKM060", path || "/", "Document nesting limit exceeded."); return; }
  if (typeof value === "string" && value.length > limits.maximumStringLength) add("PKM061", path || "/", "String length limit exceeded.");
  if (Array.isArray(value)) value.forEach((item, index) => inspectJsonValue(item, limits, add, `${path}/${index}`, depth + 1));
  else if (isRecord(value)) for (const [key, item] of Object.entries(value)) {
    if (["__proto__", "prototype", "constructor"].includes(key) || /^on/i.test(key)) add("PKM062", `${path}/${key}`, "Executable or prototype-sensitive property is forbidden.");
    inspectJsonValue(item, limits, add, `${path}/${escapePointer(key)}`, depth + 1);
  }
}

function uniqueIds(items: readonly { readonly id: string }[], path: string, add: (code: string, path: string, message: string) => void): Set<string> {
  const ids = new Set<string>();
  items.forEach((item, index) => {
    if (!validIdentifier(item.id)) add("PKM070", `${path}/${index}/id`, "ID must be portable.");
    if (ids.has(item.id)) add("PKM071", `${path}/${index}/id`, "ID is duplicated.");
    ids.add(item.id);
  });
  return ids;
}

function validateText(text: ModelerLocalizedText, path: string, add: (code: string, path: string, message: string) => void): void {
  if (!validIdentifier(text.key)) add("PKM080", `${path}/key`, "Translation key must be portable.");
  if (text.defaultText.trim().length === 0) add("PKM081", `${path}/defaultText`, "Default text is required.");
}

function validateIcon(icon: ModelerIconReference, path: string, add: (code: string, path: string, message: string) => void): void {
  if (!validIdentifier(icon.name)) add("PKM082", `${path}/name`, "Icon name must be portable.");
  if (icon.bundle !== undefined && icon.bundle !== null && !validIdentifier(icon.bundle)) add("PKM083", `${path}/bundle`, "Icon bundle must be portable.");
}

function documentContainsId(document: FormModelerDocument, id: string): boolean {
  return document.id === id || document.fields.some(item => item.id === id) || document.actions.some(item => item.id === id) || findElement(document.layout, id) !== undefined;
}

function requireIdentifier(value: string, name: string): void {
  if (!validIdentifier(value)) throw new Error(`${name} must be a portable identifier.`);
}

function assertValidLimits(limits: FormModelerLimits): void {
  for (const [name, value] of Object.entries(limits)) {
    if (!Number.isSafeInteger(value) || value < 1) throw new Error(`Modeler limit '${name}' must be a positive safe integer.`);
  }
}

function validIdentifier(value: string): boolean { return /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value); }
function validLocale(value: string): boolean { return /^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$/.test(value); }
function validJsonPointer(value: string): boolean { return value.startsWith("/") && !/(?:^|[^~])~(?:[^01]|$)/.test(value); }
function escapePointer(value: string): string { return value.replaceAll("~", "~0").replaceAll("/", "~1"); }
function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }

const modelerValueKinds = new Set<ModelerValueKind>(["string", "integer", "number", "boolean", "date", "dateTime", "time", "object", "array"]);
const modelerElementKinds = new Set<ModelerElementKind>(["control", "group", "horizontalLayout", "verticalLayout", "wizard", "step", "text", "actionBar"]);
const modelerActionKinds = new Set<ModelerActionKind>(["back", "next", "saveDraft", "skip", "cancel", "submit", "custom"]);
const componentOptionKinds = new Set<FormModelerComponentOptionKind>(["string", "boolean", "integer", "choice"]);

function validComponentOptionValue(option: FormModelerComponentOptionContract, value: string): boolean {
  if (option.kind === "boolean") return value === "true" || value === "false";
  if (option.kind === "integer") return /^-?(0|[1-9]\d*)$/.test(value) && Number.isSafeInteger(Number(value));
  if (option.kind === "choice") return option.choices?.some(choice => choice.value === value) === true;
  return value.length <= defaultFormModelerLimits.maximumStringLength;
}

function hasDocumentShape(value: unknown): value is FormModelerDocument {
  if (!isRecord(value)
    || typeof value.id !== "string"
    || typeof value.revision !== "number"
    || typeof value.name !== "string"
    || typeof value.sourceLocale !== "string"
    || !Array.isArray(value.fields)
    || !Array.isArray(value.actions)
    || !hasElementShape(value.layout)) return false;
  const fieldsValid = value.fields.every(field => isRecord(field)
    && typeof field.id === "string"
    && typeof field.dataPath === "string"
    && typeof field.valueKind === "string"
    && typeof field.required === "boolean"
    && hasTextShape(field.label));
  const actionsValid = value.actions.every(action => isRecord(action)
    && typeof action.id === "string"
    && typeof action.kind === "string"
    && typeof action.handlerId === "string"
    && typeof action.requiresValidForm === "boolean"
    && hasTextShape(action.label));
  return fieldsValid && actionsValid;
}

function hasElementShape(value: unknown): value is FormModelerElement {
  return isRecord(value)
    && typeof value.id === "string"
    && typeof value.kind === "string"
    && Array.isArray(value.elements)
    && value.elements.every(hasElementShape);
}

function hasTextShape(value: unknown): value is ModelerLocalizedText {
  return isRecord(value) && typeof value.key === "string" && typeof value.defaultText === "string";
}

function deepFreeze<T>(value: T): T {
  if (typeof value === "object" && value !== null && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const nested of Object.values(value)) deepFreeze(nested);
  }
  return value;
}
