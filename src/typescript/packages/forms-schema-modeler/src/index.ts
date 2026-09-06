export type SchemaModelerValueKind = "object" | "array" | "string" | "integer" | "number" | "boolean";
export type SchemaModelerFormat = "date" | "date-time" | "time" | "email" | "uri" | "uuid";
export type SchemaModelerEnumValue = string | number | boolean;

export interface SchemaModelerNode {
  readonly id: string;
  readonly parentId: string | null;
  readonly propertyName: string | null;
  readonly order: number;
  readonly valueKind: SchemaModelerValueKind;
  readonly required: boolean;
  readonly title?: string | null;
  readonly description?: string | null;
  readonly format?: SchemaModelerFormat | null;
  readonly enumValues?: readonly SchemaModelerEnumValue[] | null;
  readonly minimum?: number | null;
  readonly maximum?: number | null;
  readonly minimumLength?: number | null;
  readonly maximumLength?: number | null;
  readonly minimumItems?: number | null;
  readonly maximumItems?: number | null;
  readonly pattern?: string | null;
  readonly additionalProperties?: boolean | null;
}

export interface SchemaModelerDocument {
  readonly id: string;
  readonly revision: number;
  readonly schemaId: string;
  readonly title: string;
  readonly rootNodeId: string;
  readonly nodes: readonly SchemaModelerNode[];
  readonly metadata?: Readonly<Record<string, string>> | null;
}

export interface SchemaModelerLimits {
  readonly maximumNodes: number;
  readonly maximumDepth: number;
  readonly maximumStringLength: number;
  readonly maximumSourceBytes: number;
  readonly maximumHistory: number;
  readonly maximumRememberedCommands: number;
  readonly maximumEnumValues: number;
}

export const defaultSchemaModelerLimits: SchemaModelerLimits = Object.freeze({
  maximumNodes: 2_000,
  maximumDepth: 32,
  maximumStringLength: 4_096,
  maximumSourceBytes: 1_048_576,
  maximumHistory: 100,
  maximumRememberedCommands: 1_000,
  maximumEnumValues: 500
});

export interface SchemaModelerDiagnostic { readonly code: string; readonly path: string; readonly message: string; }

export type SchemaModelerOperation =
  | { readonly type: "replaceDocument"; readonly document: SchemaModelerDocument }
  | { readonly type: "insertNode"; readonly parentId: string; readonly index: number; readonly node: SchemaModelerNode }
  | { readonly type: "updateNode"; readonly node: SchemaModelerNode }
  | { readonly type: "removeNode"; readonly nodeId: string }
  | { readonly type: "moveNode"; readonly nodeId: string; readonly parentId: string; readonly index: number };

export interface SchemaModelerCommand {
  readonly commandId: string;
  readonly expectedSequence: number;
  readonly operations: readonly SchemaModelerOperation[];
}

export interface SchemaModelerSnapshot {
  readonly document: SchemaModelerDocument;
  readonly sequence: number;
  readonly selectedId?: string;
  readonly canUndo: boolean;
  readonly canRedo: boolean;
}

export class SchemaModelerValidationError extends Error {
  public constructor(public readonly diagnostics: readonly SchemaModelerDiagnostic[]) {
    super(diagnostics.map(item => `${item.code} ${item.path}: ${item.message}`).join("\n"));
    this.name = "SchemaModelerValidationError";
  }
}

export class SchemaModelerConcurrencyError extends Error {
  public constructor(public readonly expected: number, public readonly actual: number) {
    super(`The schema modeler command expected sequence ${expected}, but the current sequence is ${actual}.`);
    this.name = "SchemaModelerConcurrencyError";
  }
}

export class SchemaModelerSession {
  readonly #limits: SchemaModelerLimits;
  #document: SchemaModelerDocument;
  #sequence = 0;
  #selectedId: string | undefined;
  #undo: SchemaModelerDocument[] = [];
  #redo: SchemaModelerDocument[] = [];
  readonly #commands = new Map<string, string>();
  readonly #commandOrder: string[] = [];

  public constructor(document: SchemaModelerDocument, limits: Partial<SchemaModelerLimits> = {}) {
    this.#limits = Object.freeze({ ...defaultSchemaModelerLimits, ...limits });
    for (const [name, value] of Object.entries(this.#limits)) if (!Number.isSafeInteger(value) || value < 1) throw new Error(`Schema modeler limit '${name}' must be a positive safe integer.`);
    this.#document = validatedSnapshot(document, this.#limits);
  }

  public snapshot(): SchemaModelerSnapshot {
    return Object.freeze({
      document: this.#document,
      sequence: this.#sequence,
      ...(this.#selectedId === undefined ? {} : { selectedId: this.#selectedId }),
      canUndo: this.#undo.length > 0,
      canRedo: this.#redo.length > 0
    });
  }

  public select(id?: string): SchemaModelerSnapshot {
    if (id !== undefined && !this.#document.nodes.some(node => node.id === id)) throw new Error(`Schema node '${id}' does not exist.`);
    this.#selectedId = id;
    return this.snapshot();
  }

  public apply(command: SchemaModelerCommand): SchemaModelerSnapshot {
    requireIdentifier(command.commandId, "commandId");
    const fingerprint = JSON.stringify(command.operations);
    const previous = this.#commands.get(command.commandId);
    if (previous !== undefined) {
      if (previous !== fingerprint) throw new Error(`Command ID '${command.commandId}' was reused with different operations.`);
      return this.snapshot();
    }
    if (command.expectedSequence !== this.#sequence) throw new SchemaModelerConcurrencyError(command.expectedSequence, this.#sequence);
    if (command.operations.length === 0) throw new Error("A schema modeler command requires at least one operation.");
    let next = this.#document;
    for (const operation of command.operations) next = applyOperation(next, operation);
    next = validatedSnapshot(next, this.#limits);
    this.#undo.push(this.#document);
    if (this.#undo.length > this.#limits.maximumHistory) this.#undo.shift();
    this.#document = next;
    this.#redo = [];
    this.#sequence += 1;
    this.#commands.set(command.commandId, fingerprint);
    this.#commandOrder.push(command.commandId);
    if (this.#commandOrder.length > this.#limits.maximumRememberedCommands) {
      const forgotten = this.#commandOrder.shift();
      if (forgotten !== undefined) this.#commands.delete(forgotten);
    }
    if (this.#selectedId !== undefined && !next.nodes.some(node => node.id === this.#selectedId)) this.#selectedId = undefined;
    return this.snapshot();
  }

  public undo(): SchemaModelerSnapshot { return this.#travel(this.#undo, this.#redo); }
  public redo(): SchemaModelerSnapshot { return this.#travel(this.#redo, this.#undo); }

  #travel(source: SchemaModelerDocument[], destination: SchemaModelerDocument[]): SchemaModelerSnapshot {
    const next = source.pop();
    if (next === undefined) return this.snapshot();
    destination.push(this.#document);
    this.#document = next;
    this.#sequence += 1;
    if (this.#selectedId !== undefined && !next.nodes.some(node => node.id === this.#selectedId)) this.#selectedId = undefined;
    return this.snapshot();
  }
}

export function validateSchemaModelerDocument(document: SchemaModelerDocument, limits: SchemaModelerLimits = defaultSchemaModelerLimits): readonly SchemaModelerDiagnostic[] {
  const diagnostics: SchemaModelerDiagnostic[] = [];
  const add = (code: string, path: string, message: string) => diagnostics.push(Object.freeze({ code, path, message }));
  inspectJson(document, limits, add);
  if (!isRecord(document) || !Array.isArray(document.nodes)) {
    add("PKSM000", "/", "Document does not match the schema modeler contract.");
    return Object.freeze(diagnostics);
  }
  if (!validIdentifier(document.id)) add("PKSM001", "/id", "Document ID must be portable.");
  if (!Number.isSafeInteger(document.revision) || document.revision < 1) add("PKSM002", "/revision", "Revision must be a positive safe integer.");
  if (document.schemaId.trim().length === 0) add("PKSM003", "/schemaId", "Schema ID is required.");
  if (document.title.trim().length === 0) add("PKSM004", "/title", "Title is required.");
  if (document.nodes.length === 0 || document.nodes.length > limits.maximumNodes) add("PKSM005", "/nodes", "Node count is outside the configured bounds.");
  const byId = new Map<string, SchemaModelerNode>();
  document.nodes.forEach((node, index) => {
    const path = `/nodes/${index}`;
    if (!validIdentifier(node.id)) add("PKSM010", `${path}/id`, "Node ID must be portable.");
    if (byId.has(node.id)) add("PKSM011", `${path}/id`, "Node ID is duplicated.");
    byId.set(node.id, node);
    if (!valueKinds.has(node.valueKind)) add("PKSM012", `${path}/valueKind`, "Value kind is unsupported.");
    if (!Number.isSafeInteger(node.order) || node.order < 0) add("PKSM013", `${path}/order`, "Order must be a non-negative safe integer.");
    if (node.id === document.rootNodeId) {
      if (node.parentId !== null || node.propertyName !== null || node.required || node.order !== 0) add("PKSM014", path, "The root node cannot have a parent, property name, required flag or nonzero order.");
    } else if (node.parentId === null) add("PKSM015", `${path}/parentId`, "Only the root node may omit its parent.");
    if (node.parentId !== null && !byId.has(node.parentId) && !document.nodes.some(candidate => candidate.id === node.parentId)) add("PKSM016", `${path}/parentId`, "Parent node does not exist.");
    validateNodeConstraints(node, path, add, limits);
  });
  const root = byId.get(document.rootNodeId);
  if (root === undefined) add("PKSM020", "/rootNodeId", "Root node does not exist.");
  const childrenByParent = new Map<string, SchemaModelerNode[]>();
  for (const node of document.nodes) if (node.parentId !== null) {
    const children = childrenByParent.get(node.parentId) ?? [];
    children.push(node);
    childrenByParent.set(node.parentId, children);
  }
  for (const parent of document.nodes) {
    const children = childrenByParent.get(parent.id) ?? [];
    const ordered = [...children].sort((left, right) => left.order - right.order);
    ordered.forEach((child, index) => { if (child.order !== index) add("PKSM021", `/nodes/${document.nodes.indexOf(child)}/order`, "Sibling order must be contiguous and unique."); });
    if (children.length > 0 && parent.valueKind !== "object" && parent.valueKind !== "array") add("PKSM022", `/nodes/${document.nodes.indexOf(parent)}`, "Scalar nodes cannot contain children.");
    if (parent.valueKind === "array" && children.length !== 1) add("PKSM023", `/nodes/${document.nodes.indexOf(parent)}`, "Array nodes require exactly one item schema.");
    const propertyNames = new Set<string>();
    for (const child of children) {
      if (parent.valueKind === "object") {
        if (child.propertyName === null || child.propertyName.length === 0) add("PKSM024", `/nodes/${document.nodes.indexOf(child)}/propertyName`, "Object children require property names.");
        else if (propertyNames.has(child.propertyName)) add("PKSM025", `/nodes/${document.nodes.indexOf(child)}/propertyName`, "Property name is duplicated within its object.");
        else propertyNames.add(child.propertyName);
      } else if (child.propertyName !== null || child.required) add("PKSM026", `/nodes/${document.nodes.indexOf(child)}`, "Array item schemas cannot have property names or required flags.");
    }
  }
  for (const node of document.nodes) {
    const seen = new Set<string>();
    let current: SchemaModelerNode | undefined = node;
    let depth = 0;
    while (current?.parentId !== null && current !== undefined) {
      if (seen.has(current.id)) { add("PKSM027", `/nodes/${document.nodes.indexOf(node)}`, "Schema hierarchy contains a cycle."); break; }
      seen.add(current.id);
      current = byId.get(current.parentId);
      depth += 1;
      if (depth > limits.maximumDepth) { add("PKSM028", `/nodes/${document.nodes.indexOf(node)}`, "Schema hierarchy exceeds the depth limit."); break; }
    }
  }
  return Object.freeze(diagnostics);
}

export function compileSchemaModelerDocument(document: SchemaModelerDocument): Readonly<Record<string, unknown>> {
  const valid = validatedSnapshot(document, defaultSchemaModelerLimits);
  const byId = new Map(valid.nodes.map(node => [node.id, node]));
  const children = (parentId: string) => valid.nodes.filter(node => node.parentId === parentId).sort((left, right) => left.order - right.order);
  const compile = (node: SchemaModelerNode): Record<string, unknown> => {
    const schema: Record<string, unknown> = { type: node.valueKind };
    if (node.title != null) schema.title = node.title;
    if (node.description != null) schema.description = node.description;
    if (node.format != null) schema.format = node.format;
    if (node.enumValues != null) schema.enum = [...node.enumValues];
    copyConstraint(schema, "minimum", node.minimum);
    copyConstraint(schema, "maximum", node.maximum);
    copyConstraint(schema, "minLength", node.minimumLength);
    copyConstraint(schema, "maxLength", node.maximumLength);
    copyConstraint(schema, "minItems", node.minimumItems);
    copyConstraint(schema, "maxItems", node.maximumItems);
    if (node.pattern != null) schema.pattern = node.pattern;
    if (node.valueKind === "object") {
      const objectChildren = children(node.id);
      schema.properties = Object.fromEntries(objectChildren.map(child => [child.propertyName as string, compile(child)]));
      const required = objectChildren.filter(child => child.required).map(child => child.propertyName as string);
      if (required.length > 0) schema.required = required;
      schema.additionalProperties = node.additionalProperties === true;
    } else if (node.valueKind === "array") {
      const item = children(node.id)[0];
      if (item === undefined) throw new Error(`Array node '${node.id}' has no item schema.`);
      schema.items = compile(item);
    }
    return schema;
  };
  const root = byId.get(valid.rootNodeId);
  if (root === undefined) throw new Error("Schema root does not exist.");
  return deepFreeze({
    $schema: "https://json-schema.org/draft/2020-12/schema",
    $id: valid.schemaId,
    title: valid.title,
    ...compile(root)
  });
}

export function serializeCompiledJsonSchema(document: SchemaModelerDocument): string {
  return JSON.stringify(compileSchemaModelerDocument(document), null, 2) + "\n";
}

export function parseCompiledJsonSchema(source: string, documentId = "schema", revision = 1, limits: SchemaModelerLimits = defaultSchemaModelerLimits): SchemaModelerDocument {
  if (new TextEncoder().encode(source).byteLength > limits.maximumSourceBytes) throw new Error("The JSON Schema source exceeds the configured byte limit.");
  const raw: unknown = JSON.parse(source);
  if (!isRecord(raw)) throw new Error("The JSON Schema root must be an object.");
  if (raw.$schema !== undefined && raw.$schema !== "https://json-schema.org/draft/2020-12/schema") throw new Error("Only JSON Schema 2020-12 documents are accepted.");
  if (raw.$id !== undefined && typeof raw.$id !== "string") throw new Error("JSON Schema '$id' must be a string.");
  const nodes: SchemaModelerNode[] = [];
  const visit = (schema: Record<string, unknown>, parentId: string | null, propertyName: string | null, order: number, required: boolean, suggestedId: string): string => {
    rejectUnknownKeywords(schema);
    const valueKind = schema.type;
    if (typeof valueKind !== "string" || !valueKinds.has(valueKind as SchemaModelerValueKind)) throw new Error(`Schema node '${suggestedId}' requires one supported explicit type.`);
    assertKeywordApplicability(schema, valueKind as SchemaModelerValueKind, suggestedId);
    const id = uniqueNodeId(nodes, suggestedId);
    const node: SchemaModelerNode = {
      id, parentId, propertyName, order, valueKind: valueKind as SchemaModelerValueKind, required,
      ...optionalString(schema, "title"), ...optionalString(schema, "description"),
      ...(schema.format === undefined ? {} : { format: schema.format as SchemaModelerFormat }),
      ...(schema.enum === undefined ? {} : { enumValues: schema.enum as SchemaModelerEnumValue[] }),
      ...optionalNumber(schema, "minimum"), ...optionalNumber(schema, "maximum"),
      ...renamedNumber(schema, "minLength", "minimumLength"), ...renamedNumber(schema, "maxLength", "maximumLength"),
      ...renamedNumber(schema, "minItems", "minimumItems"), ...renamedNumber(schema, "maxItems", "maximumItems"),
      ...optionalString(schema, "pattern"),
      ...(valueKind === "object" ? { additionalProperties: schema.additionalProperties === true } : {})
    };
    nodes.push(node);
    if (valueKind === "object") {
      const properties = schema.properties === undefined ? {} : schema.properties;
      if (!isRecord(properties)) throw new Error(`Object schema '${id}' requires an object properties map.`);
      const requiredNames = Array.isArray(schema.required) ? schema.required : [];
      if (requiredNames.some(name => typeof name !== "string")) throw new Error(`Object schema '${id}' has an invalid required list.`);
      if (new Set(requiredNames).size !== requiredNames.length) throw new Error(`Object schema '${id}' repeats a required property.`);
      for (const name of requiredNames) if (!Object.hasOwn(properties, name as string)) throw new Error(`Object schema '${id}' requires unknown property '${name}'.`);
      Object.entries(properties).forEach(([name, child], index) => {
        if (!isRecord(child)) throw new Error(`Property '${name}' must contain a schema object.`);
        visit(child, id, name, index, requiredNames.includes(name), `${id}-${portableSegment(name)}`);
      });
    } else if (valueKind === "array") {
      if (!isRecord(schema.items)) throw new Error(`Array schema '${id}' requires one item schema.`);
      visit(schema.items, id, null, 0, false, `${id}-item`);
    }
    return id;
  };
  const rootNodeId = visit(raw, null, null, 0, false, "root");
  return validatedSnapshot({
    id: documentId,
    revision,
    schemaId: typeof raw.$id === "string" ? raw.$id : `urn:program-kit:schema:${documentId}:${revision}`,
    title: typeof raw.title === "string" && raw.title.trim().length > 0 ? raw.title : documentId,
    rootNodeId,
    nodes
  }, limits);
}

export interface SchemaModelerGraphNode { readonly id: string; readonly label: string; readonly valueKind: SchemaModelerValueKind; }
export interface SchemaModelerGraphEdge { readonly from: string; readonly to: string; readonly kind: "property" | "items"; readonly label?: string; }
export interface SchemaModelerGraph { readonly nodes: readonly SchemaModelerGraphNode[]; readonly edges: readonly SchemaModelerGraphEdge[]; }

export function projectSchemaModelerGraph(document: SchemaModelerDocument): SchemaModelerGraph {
  const valid = validatedSnapshot(document, defaultSchemaModelerLimits);
  return Object.freeze({
    nodes: Object.freeze(valid.nodes.map(node => Object.freeze({ id: node.id, label: node.title ?? node.propertyName ?? valid.title, valueKind: node.valueKind }))),
    edges: Object.freeze(valid.nodes.flatMap(node => node.parentId === null ? [] : [Object.freeze({ from: node.parentId, to: node.id, kind: node.propertyName === null ? "items" as const : "property" as const, ...(node.propertyName === null ? {} : { label: node.propertyName }) })]))
  });
}

export function listSchemaModelerChildren(document: SchemaModelerDocument, parentId: string): readonly SchemaModelerNode[] {
  return Object.freeze(document.nodes.filter(node => node.parentId === parentId).sort((left, right) => left.order - right.order));
}

function applyOperation(document: SchemaModelerDocument, operation: SchemaModelerOperation): SchemaModelerDocument {
  if (operation.type === "replaceDocument") return operation.document;
  if (operation.type === "updateNode") {
    if (!document.nodes.some(node => node.id === operation.node.id)) throw new Error(`Schema node '${operation.node.id}' does not exist.`);
    return { ...document, nodes: document.nodes.map(node => node.id === operation.node.id ? operation.node : node) };
  }
  if (operation.type === "insertNode") {
    if (document.nodes.some(node => node.id === operation.node.id)) throw new Error(`Schema node '${operation.node.id}' already exists.`);
    const parent = document.nodes.find(node => node.id === operation.parentId);
    if (parent === undefined) throw new Error(`Schema parent '${operation.parentId}' does not exist.`);
    if (parent.valueKind !== "object" && parent.valueKind !== "array") throw new Error("Only object and array schemas can contain nodes.");
    const siblings = listSchemaModelerChildren(document, operation.parentId);
    if (!Number.isSafeInteger(operation.index) || operation.index < 0 || operation.index > siblings.length) throw new Error("Schema insertion index is outside the sibling range.");
    const shifted = document.nodes.map(node => node.parentId === operation.parentId && node.order >= operation.index ? { ...node, order: node.order + 1 } : node);
    return { ...document, nodes: [...shifted, { ...operation.node, parentId: operation.parentId, order: operation.index }] };
  }
  if (operation.nodeId === document.rootNodeId) throw new Error("The root schema node cannot be removed or moved.");
  const moving = document.nodes.find(node => node.id === operation.nodeId);
  if (moving === undefined) throw new Error(`Schema node '${operation.nodeId}' does not exist.`);
  if (operation.type === "removeNode") {
    const removed = descendants(document, operation.nodeId);
    removed.add(operation.nodeId);
    const remaining = document.nodes.filter(node => !removed.has(node.id));
    return { ...document, nodes: normalizeOrders(remaining) };
  }
  const parent = document.nodes.find(node => node.id === operation.parentId);
  if (parent === undefined || parent.valueKind !== "object" && parent.valueKind !== "array") throw new Error(`Schema move target '${operation.parentId}' is not a container.`);
  if (descendants(document, operation.nodeId).has(operation.parentId)) throw new Error("A schema node cannot move into its descendant.");
  const without = normalizeOrders(document.nodes.filter(node => node.id !== operation.nodeId));
  const siblings = without.filter(node => node.parentId === operation.parentId);
  if (!Number.isSafeInteger(operation.index) || operation.index < 0 || operation.index > siblings.length) throw new Error("Schema move index is outside the sibling range.");
  const shifted = without.map(node => node.parentId === operation.parentId && node.order >= operation.index ? { ...node, order: node.order + 1 } : node);
  return { ...document, nodes: [...shifted, { ...moving, parentId: operation.parentId, order: operation.index }] };
}

function validateNodeConstraints(node: SchemaModelerNode, path: string, add: (code: string, path: string, message: string) => void, limits: SchemaModelerLimits): void {
  if (node.format != null && (!formats.has(node.format) || node.valueKind !== "string")) add("PKSM030", `${path}/format`, "Format must be an allowlisted string format.");
  if ((node.minimum != null || node.maximum != null) && node.valueKind !== "number" && node.valueKind !== "integer") add("PKSM031", path, "Numeric bounds apply only to numbers and integers.");
  if (node.minimum != null && node.maximum != null && node.minimum > node.maximum) add("PKSM032", path, "Minimum cannot exceed maximum.");
  if ((node.minimumLength != null || node.maximumLength != null || node.pattern != null) && node.valueKind !== "string") add("PKSM033", path, "Text constraints apply only to strings.");
  if ((node.minimumItems != null || node.maximumItems != null) && node.valueKind !== "array") add("PKSM034", path, "Item constraints apply only to arrays.");
  for (const value of [node.minimumLength, node.maximumLength, node.minimumItems, node.maximumItems]) if (value != null && (!Number.isSafeInteger(value) || value < 0)) add("PKSM035", path, "Length and item bounds must be non-negative safe integers.");
  if (node.enumValues != null) {
    if (node.enumValues.length === 0 || node.enumValues.length > limits.maximumEnumValues) add("PKSM036", `${path}/enumValues`, "Enum value count is outside the configured bounds.");
    const identities = node.enumValues.map(value => JSON.stringify(value));
    if (new Set(identities).size !== identities.length) add("PKSM037", `${path}/enumValues`, "Enum values must be unique.");
    if (node.enumValues.some(value => !enumMatchesKind(value, node.valueKind))) add("PKSM039", `${path}/enumValues`, "Enum values must match the node value kind.");
  }
  if (node.additionalProperties != null && node.valueKind !== "object") add("PKSM038", `${path}/additionalProperties`, "Only object nodes configure additional properties.");
}

function validatedSnapshot(document: SchemaModelerDocument, limits: SchemaModelerLimits): SchemaModelerDocument {
  const clone = JSON.parse(JSON.stringify(document)) as SchemaModelerDocument;
  const diagnostics = validateSchemaModelerDocument(clone, limits);
  if (diagnostics.length > 0) throw new SchemaModelerValidationError(diagnostics);
  return deepFreeze(clone);
}

function descendants(document: SchemaModelerDocument, nodeId: string): Set<string> {
  const result = new Set<string>();
  const visit = (id: string): void => { for (const child of document.nodes.filter(node => node.parentId === id)) { result.add(child.id); visit(child.id); } };
  visit(nodeId);
  return result;
}

function normalizeOrders(nodes: readonly SchemaModelerNode[]): readonly SchemaModelerNode[] {
  const groups = new Map<string | null, SchemaModelerNode[]>();
  for (const node of nodes) { const group = groups.get(node.parentId) ?? []; group.push(node); groups.set(node.parentId, group); }
  const orders = new Map<string, number>();
  for (const group of groups.values()) [...group].sort((a, b) => a.order - b.order).forEach((node, index) => orders.set(node.id, index));
  return nodes.map(node => ({ ...node, order: orders.get(node.id) ?? node.order }));
}

function rejectUnknownKeywords(schema: Record<string, unknown>): void {
  for (const key of Object.keys(schema)) if (!allowedKeywords.has(key)) throw new Error(`JSON Schema keyword '${key}' is outside the governed modeler subset.`);
}

function assertKeywordApplicability(schema: Record<string, unknown>, valueKind: SchemaModelerValueKind, nodeId: string): void {
  if (schema.additionalProperties !== undefined && typeof schema.additionalProperties !== "boolean") throw new Error(`Object schema '${nodeId}' requires Boolean additionalProperties.`);
  if (valueKind !== "object" && ["properties", "required", "additionalProperties"].some(key => schema[key] !== undefined)) throw new Error(`Non-object schema '${nodeId}' contains object-only keywords.`);
  if (valueKind !== "array" && ["items", "minItems", "maxItems"].some(key => schema[key] !== undefined)) throw new Error(`Non-array schema '${nodeId}' contains array-only keywords.`);
  if (valueKind !== "string" && ["minLength", "maxLength", "pattern", "format"].some(key => schema[key] !== undefined)) throw new Error(`Non-string schema '${nodeId}' contains string-only keywords.`);
  if (valueKind !== "number" && valueKind !== "integer" && ["minimum", "maximum"].some(key => schema[key] !== undefined)) throw new Error(`Non-numeric schema '${nodeId}' contains numeric-only keywords.`);
  if (schema.enum !== undefined && (!Array.isArray(schema.enum) || schema.enum.length === 0 || schema.enum.some(value => !enumMatchesKind(value, valueKind)))) throw new Error(`Schema '${nodeId}' has enum values that do not match its type.`);
  if (schema.required !== undefined && !Array.isArray(schema.required)) throw new Error(`Object schema '${nodeId}' requires an array-valued required keyword.`);
}

function optionalString(schema: Record<string, unknown>, key: "title" | "description" | "pattern"): Partial<SchemaModelerNode> {
  const value = schema[key];
  if (value === undefined) return {};
  if (typeof value !== "string") throw new Error(`JSON Schema '${key}' must be a string.`);
  return { [key]: value };
}

function optionalNumber(schema: Record<string, unknown>, key: "minimum" | "maximum"): Partial<SchemaModelerNode> {
  const value = schema[key];
  if (value === undefined) return {};
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`JSON Schema '${key}' must be finite.`);
  return { [key]: value };
}

function renamedNumber(schema: Record<string, unknown>, source: "minLength" | "maxLength" | "minItems" | "maxItems", target: "minimumLength" | "maximumLength" | "minimumItems" | "maximumItems"): Partial<SchemaModelerNode> {
  const value = schema[source];
  if (value === undefined) return {};
  if (typeof value !== "number") throw new Error(`JSON Schema '${source}' must be numeric.`);
  return { [target]: value };
}

function uniqueNodeId(nodes: readonly SchemaModelerNode[], suggested: string): string {
  let candidate = portableSegment(suggested);
  let suffix = 2;
  while (nodes.some(node => node.id === candidate)) candidate = `${portableSegment(suggested)}-${suffix++}`;
  return candidate;
}

function portableSegment(value: string): string {
  const result = value.replace(/[^A-Za-z0-9._:-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 96);
  return result.length === 0 ? "node" : /^[A-Za-z0-9]/.test(result) ? result : `node-${result}`;
}

function inspectJson(value: unknown, limits: SchemaModelerLimits, add: (code: string, path: string, message: string) => void, path = "", depth = 0): void {
  if (depth > limits.maximumDepth + 8) { add("PKSM040", path || "/", "Document nesting exceeds the configured limit."); return; }
  if (typeof value === "string" && value.length > limits.maximumStringLength) add("PKSM041", path || "/", "String exceeds the configured limit.");
  if (Array.isArray(value)) value.forEach((item, index) => inspectJson(item, limits, add, `${path}/${index}`, depth + 1));
  else if (isRecord(value)) for (const [key, item] of Object.entries(value)) {
    if (["__proto__", "prototype", "constructor"].includes(key) || /^on/i.test(key)) add("PKSM042", `${path}/${key}`, "Prototype-sensitive or executable property is forbidden.");
    inspectJson(item, limits, add, `${path}/${escapePointer(key)}`, depth + 1);
  }
}

function copyConstraint(target: Record<string, unknown>, key: string, value: number | null | undefined): void { if (value != null) target[key] = value; }
function enumMatchesKind(value: unknown, kind: SchemaModelerValueKind): value is SchemaModelerEnumValue {
  return kind === "string" ? typeof value === "string" : kind === "boolean" ? typeof value === "boolean" : kind === "integer" ? typeof value === "number" && Number.isSafeInteger(value) : kind === "number" ? typeof value === "number" && Number.isFinite(value) : false;
}
function requireIdentifier(value: string, name: string): void { if (!validIdentifier(value)) throw new Error(`${name} must be a portable identifier.`); }
function validIdentifier(value: string): boolean { return /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value); }
function escapePointer(value: string): string { return value.replaceAll("~", "~0").replaceAll("/", "~1"); }
function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function deepFreeze<T>(value: T): T { if (typeof value === "object" && value !== null && !Object.isFrozen(value)) { Object.freeze(value); for (const child of Object.values(value)) deepFreeze(child); } return value; }

const valueKinds = new Set<SchemaModelerValueKind>(["object", "array", "string", "integer", "number", "boolean"]);
const formats = new Set<SchemaModelerFormat>(["date", "date-time", "time", "email", "uri", "uuid"]);
const allowedKeywords = new Set(["$schema", "$id", "title", "description", "type", "properties", "required", "items", "additionalProperties", "enum", "format", "minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems", "pattern"]);
