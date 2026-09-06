import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch, type PropType, type VNode } from "vue";
import { codeMirrorJsonEditorAdapter } from "@orbyss/program-kit-forms-codemirror";
import type { JsonEditorAdapter, JsonEditorHandle } from "@orbyss/program-kit-forms-editor-contracts";
import {
  SchemaModelerSession,
  SchemaModelerValidationError,
  listSchemaModelerChildren,
  parseCompiledJsonSchema,
  projectSchemaModelerGraph,
  serializeCompiledJsonSchema,
  type SchemaModelerDocument,
  type SchemaModelerNode,
  type SchemaModelerOperation,
  type SchemaModelerSnapshot,
  type SchemaModelerValueKind
} from "@orbyss/program-kit-forms-schema-modeler";
import { programKitClassName, type ProgramKitClassNames } from "@orbyss/program-kit-ui-theme";

export type SchemaModelerVueView = "design" | "json" | "graph";
export type SchemaModelerVueEditorMode = "rich" | "strictCsp";
export type SchemaModelerVueThemeSlot = "root" | "toolbar" | "diagnostics" | "tabs" | "workspace" | "palette" | "tree" | "canvas" | "canvasBlock" | "inspector" | "editor" | "graph" | "graphNode";

export interface ProgramKitSchemaModelerVueLabels {
  readonly undo: string; readonly redo: string; readonly commit: string; readonly applyJson: string;
  readonly design: string; readonly json: string; readonly graph: string; readonly palette: string;
  readonly structure: string; readonly canvas: string; readonly inspector: string; readonly editor: string;
  readonly remove: string;
}

const labelsDefault: ProgramKitSchemaModelerVueLabels = Object.freeze({
  undo: "Undo", redo: "Redo", commit: "Commit schema", applyJson: "Apply JSON Schema",
  design: "Design", json: "JSON Schema", graph: "Graph", palette: "Schema types",
  structure: "Schema structure", canvas: "Schema canvas", inspector: "Properties",
  editor: "JSON Schema source", remove: "Remove node"
});

function slot(name: SchemaModelerVueThemeSlot, defaultClass: string, classNames: ProgramKitClassNames<SchemaModelerVueThemeSlot>, unstyled: boolean, extra?: string) {
  return { class: programKitClassName(defaultClass, [classNames[name], extra].filter(Boolean).join(" ") || undefined, unstyled), "data-pk-slot": `schema-modeler.${name}` };
}

export const ProgramKitSchemaJsonEditorVue = defineComponent({
  name: "ProgramKitSchemaJsonEditorVue",
  props: {
    source: { type: String, required: true },
    accessibleLabel: { type: String, required: true },
    adapter: { type: Object as PropType<JsonEditorAdapter>, default: () => codeMirrorJsonEditorAdapter },
    mode: { type: String as PropType<SchemaModelerVueEditorMode>, default: "rich" },
    cspNonce: { type: String, required: false },
    classNames: { type: Object as PropType<ProgramKitClassNames<SchemaModelerVueThemeSlot>>, default: () => ({}) },
    unstyled: { type: Boolean, default: false }
  },
  emits: { change: (value: string) => typeof value === "string" },
  setup(props, { emit }) {
    const parent = ref<HTMLElement>();
    let handle: JsonEditorHandle | undefined;
    const destroy = () => { handle?.destroy(); handle = undefined; };
    const mount = () => {
      destroy();
      if (props.mode === "strictCsp" || parent.value === undefined) return;
      handle = props.adapter.mount({ parent: parent.value, document: props.source, accessibleLabel: props.accessibleLabel, onChange: value => emit("change", value), diagnostics: schemaDiagnostics, ...(props.cspNonce === undefined ? {} : { cspNonce: props.cspNonce }) });
    };
    onMounted(mount);
    onBeforeUnmount(destroy);
    watch(() => [props.adapter, props.mode, props.accessibleLabel, props.cspNonce], mount);
    watch(() => props.source, value => handle?.setDocument(value));
    return () => props.mode === "strictCsp"
      ? h("textarea", { ...slot("editor", "pk-schema-modeler__editor pk-schema-modeler__editor--strict", props.classNames, props.unstyled), "aria-label": props.accessibleLabel, value: props.source, spellcheck: false, onInput: (event: Event) => emit("change", (event.currentTarget as HTMLTextAreaElement).value) })
      : h("div", { ...slot("editor", "pk-schema-modeler__editor", props.classNames, props.unstyled), ref: parent });
  }
});

export const ProgramKitSchemaModelerVue = defineComponent({
  name: "ProgramKitSchemaModelerVue",
  props: {
    session: { type: Object as PropType<SchemaModelerSession>, required: true },
    initialView: { type: String as PropType<SchemaModelerVueView>, default: "design" },
    labels: { type: Object as PropType<Partial<ProgramKitSchemaModelerVueLabels>>, default: () => ({}) },
    editorMode: { type: String as PropType<SchemaModelerVueEditorMode>, default: "rich" },
    editorAdapter: { type: Object as PropType<JsonEditorAdapter>, default: () => codeMirrorJsonEditorAdapter },
    cspNonce: { type: String, required: false },
    classNames: { type: Object as PropType<ProgramKitClassNames<SchemaModelerVueThemeSlot>>, default: () => ({}) },
    className: { type: String, required: false },
    unstyled: { type: Boolean, default: false }
  },
  emits: {
    change: (snapshot: SchemaModelerSnapshot) => snapshot !== null,
    commit: (document: SchemaModelerDocument, sequence: number) => document !== null && Number.isSafeInteger(sequence)
  },
  setup(props, { emit }) {
    const labels = computed(() => ({ ...labelsDefault, ...props.labels }));
    const snapshot = ref(props.session.snapshot());
    const view = ref<SchemaModelerVueView>(props.initialView);
    const source = ref(serializeCompiledJsonSchema(snapshot.value.document));
    const error = ref("");
    const refresh = (next: SchemaModelerSnapshot) => { snapshot.value = next; source.value = serializeCompiledJsonSchema(next.document); error.value = ""; emit("change", next); };
    const apply = (operations: readonly SchemaModelerOperation[]) => {
      try { refresh(props.session.apply({ commandId: `schema-vue:${snapshot.value.sequence}:${counter++}`, expectedSequence: snapshot.value.sequence, operations })); }
      catch (reason) { error.value = publicError(reason); }
    };
    const select = (id: string) => refresh(props.session.select(id));
    const applySource = () => {
      try { apply([{ type: "replaceDocument", document: parseCompiledJsonSchema(source.value, snapshot.value.document.id, snapshot.value.document.revision) }]); }
      catch (reason) { error.value = publicError(reason); }
    };
    const tab = (target: SchemaModelerVueView, text: string) => h("button", { role: "tab", "aria-selected": view.value === target, tabindex: view.value === target ? 0 : -1, onClick: () => { view.value = target; }, type: "button" }, text);
    return () => h("section", slot("root", "pk-schema-modeler", props.classNames, props.unstyled, props.className), [
      h("div", slot("toolbar", "pk-schema-modeler__toolbar", props.classNames, props.unstyled), [
        h("button", { disabled: !snapshot.value.canUndo, onClick: () => refresh(props.session.undo()), type: "button" }, labels.value.undo),
        h("button", { disabled: !snapshot.value.canRedo, onClick: () => refresh(props.session.redo()), type: "button" }, labels.value.redo),
        h("button", { onClick: () => emit("commit", snapshot.value.document, snapshot.value.sequence), type: "button" }, labels.value.commit)
      ]),
      error.value.length === 0 ? null : h("p", { ...slot("diagnostics", "pk-schema-modeler__diagnostics", props.classNames, props.unstyled), role: "alert" }, error.value),
      h("div", { ...slot("tabs", "pk-schema-modeler__tabs", props.classNames, props.unstyled), role: "tablist", "aria-label": "Schema modeler views" }, [tab("design", labels.value.design), tab("json", labels.value.json), tab("graph", labels.value.graph)]),
      view.value === "design" ? designView(snapshot.value, labels.value, props.classNames, props.unstyled, select, apply) : null,
      view.value === "json" ? h("section", { role: "tabpanel" }, [
        h(ProgramKitSchemaJsonEditorVue, { source: source.value, accessibleLabel: labels.value.editor, adapter: props.editorAdapter, mode: props.editorMode, classNames: props.classNames, unstyled: props.unstyled, ...(props.cspNonce === undefined ? {} : { cspNonce: props.cspNonce }), onChange: (value: string) => { source.value = value; } }),
        h("button", { onClick: applySource, type: "button" }, labels.value.applyJson)
      ]) : null,
      view.value === "graph" ? graphView(snapshot.value, props.classNames, props.unstyled, select) : null
    ]);
  }
});

function designView(snapshot: SchemaModelerSnapshot, labels: ProgramKitSchemaModelerVueLabels, classNames: ProgramKitClassNames<SchemaModelerVueThemeSlot>, unstyled: boolean, select: (id: string) => void, apply: (operations: readonly SchemaModelerOperation[]) => void): VNode {
  const document = snapshot.document;
  const selected = document.nodes.find(node => node.id === snapshot.selectedId);
  const parent = selected !== undefined && (selected.valueKind === "object" || selected.valueKind === "array") ? selected : document.nodes.find(node => node.id === selected?.parentId) ?? document.nodes.find(node => node.id === document.rootNodeId);
  const children = parent === undefined ? [] : listSchemaModelerChildren(document, parent.id);
  const add = (kind: SchemaModelerValueKind) => {
    if (parent === undefined || parent.valueKind === "array" && children.length > 0) return;
    const id = nextId(document, kind);
    const node: SchemaModelerNode = { id, parentId: parent.id, propertyName: parent.valueKind === "object" ? nextProperty(children, kind) : null, order: children.length, valueKind: kind, required: false, ...(kind === "object" ? { additionalProperties: false } : {}) };
    const operations: SchemaModelerOperation[] = [{ type: "insertNode", parentId: parent.id, index: children.length, node }];
    if (kind === "array") operations.push({ type: "insertNode", parentId: id, index: 0, node: { id: `${id}-item`, parentId: id, propertyName: null, order: 0, valueKind: "string", required: false } });
    apply(operations);
  };
  const root = document.nodes.find(node => node.id === document.rootNodeId);
  const treeNode = (node: SchemaModelerNode): VNode => h("li", { key: node.id }, [h("button", { "aria-current": snapshot.selectedId === node.id, onClick: () => select(node.id), type: "button" }, [node.propertyName ?? document.title, h("small", node.valueKind)]), ...(listSchemaModelerChildren(document, node.id).length === 0 ? [] : [h("ul", listSchemaModelerChildren(document, node.id).map(treeNode))])]);
  const block = (node: SchemaModelerNode): VNode => h("div", { ...slot("canvasBlock", "pk-schema-modeler__block", classNames, unstyled), key: node.id }, [h("button", { "aria-pressed": snapshot.selectedId === node.id, onClick: () => select(node.id), type: "button" }, [h("strong", node.propertyName ?? document.title), h("small", `${node.valueKind}${node.required ? " · required" : ""}`)]), ...listSchemaModelerChildren(document, node.id).map(block)]);
  const inspected = selected ?? root;
  return h("section", slot("workspace", "pk-schema-modeler__workspace", classNames, unstyled), [
    h("aside", { ...slot("palette", "pk-schema-modeler__palette", classNames, unstyled), "aria-label": labels.palette }, [h("h2", labels.palette), ...(["string", "integer", "number", "boolean", "object", "array"] as const).map(kind => h("button", { disabled: parent === undefined || parent.valueKind === "array" && children.length > 0, onClick: () => add(kind), type: "button" }, `Add ${kind}`))]),
    h("nav", { ...slot("tree", "pk-schema-modeler__tree", classNames, unstyled), "aria-label": labels.structure }, [h("h2", labels.structure), root === undefined ? null : h("ul", [treeNode(root)])]),
    h("section", { ...slot("canvas", "pk-schema-modeler__canvas", classNames, unstyled), "aria-label": labels.canvas }, [h("h2", labels.canvas), root === undefined ? null : block(root)]),
    h("aside", { ...slot("inspector", "pk-schema-modeler__inspector", classNames, unstyled), "aria-label": labels.inspector }, inspected === undefined ? [] : [
      h("h2", labels.inspector), h("dl", [h("dt", "ID"), h("dd", inspected.id), h("dt", "Type"), h("dd", inspected.valueKind)]),
      inspected.propertyName === null ? null : h("label", ["Property name", h("input", { value: inspected.propertyName, onChange: (event: Event) => apply([{ type: "updateNode", node: { ...inspected, propertyName: (event.currentTarget as HTMLInputElement).value } }]) })]),
      h("label", ["Title", h("input", { value: inspected.title ?? "", onChange: (event: Event) => { const value = (event.currentTarget as HTMLInputElement).value; apply([{ type: "updateNode", node: { ...inspected, title: value.length === 0 ? null : value } }]); } })]),
      inspected.propertyName === null ? null : h("label", [h("input", { type: "checkbox", checked: inspected.required, onChange: (event: Event) => apply([{ type: "updateNode", node: { ...inspected, required: (event.currentTarget as HTMLInputElement).checked } }]) }), " Required"]),
      inspected.id === document.rootNodeId ? null : h("button", { onClick: () => apply([{ type: "removeNode", nodeId: inspected.id }]), type: "button" }, labels.remove)
    ])
  ]);
}

function graphView(snapshot: SchemaModelerSnapshot, classNames: ProgramKitClassNames<SchemaModelerVueThemeSlot>, unstyled: boolean, select: (id: string) => void): VNode {
  const graph = projectSchemaModelerGraph(snapshot.document);
  return h("section", { ...slot("graph", "pk-schema-modeler__graph", classNames, unstyled), role: "tabpanel" }, [
    h("div", { class: "pk-schema-modeler__graph-nodes" }, graph.nodes.map(node => h("button", { ...slot("graphNode", "pk-schema-modeler__graph-node", classNames, unstyled), "aria-pressed": snapshot.selectedId === node.id, onClick: () => select(node.id), type: "button" }, [h("strong", node.label), h("small", node.valueKind)]))),
    h("table", [h("thead", [h("tr", [h("th", "From"), h("th", "Relationship"), h("th", "To")])]), h("tbody", graph.edges.map(edge => h("tr", [h("td", edge.from), h("td", edge.label ?? edge.kind), h("td", edge.to)])))])
  ]);
}

function schemaDiagnostics(source: string) { try { parseCompiledJsonSchema(source); return []; } catch (error) { return [{ from: 0, to: source.length, severity: "error" as const, message: publicError(error) }]; } }
function publicError(error: unknown): string { return error instanceof SchemaModelerValidationError || error instanceof Error ? error.message : "The schema operation could not be completed."; }
function nextId(document: SchemaModelerDocument, kind: string): string { let index = 1; while (document.nodes.some(node => node.id === `${kind}-${index}` || node.id === `${kind}-${index}-item`)) index += 1; return `${kind}-${index}`; }
function nextProperty(children: readonly SchemaModelerNode[], kind: string): string { let index = 1; while (children.some(node => node.propertyName === `${kind}${index}`)) index += 1; return `${kind}${index}`; }
let counter = 1;
