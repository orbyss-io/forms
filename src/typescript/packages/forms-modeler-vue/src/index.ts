import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch, type PropType, type VNode, type VNodeChild } from "vue";
import { codeMirrorJsonEditorAdapter } from "@orbyss/program-kit-forms-codemirror";
import type { JsonEditorAdapter, JsonEditorDiagnostic, JsonEditorHandle } from "@orbyss/program-kit-forms-editor-contracts";
import {
  FormModelerSession,
  getFormModelerElementPlacement,
  listFormModelerMoveTargets,
  parseFormModelerDocument,
  projectFormModelerGraph,
  serializeFormModelerDocument,
  type FormModelerAction,
  type FormModelerActionCatalog,
  type FormModelerComponentCatalog,
  type FormModelerComponentContract,
  type FormModelerDocument,
  type FormModelerElement,
  type FormModelerField,
  type FormModelerOperation,
  type FormModelerSnapshot
} from "@orbyss/program-kit-forms-modeler";
import { programKitClassName, type ProgramKitClassNames } from "@orbyss/program-kit-ui-theme";

export type FormModelerVueView = "design" | "json" | "graph";
export type FormModelerVueEditorMode = "rich" | "strictCsp";
export type FormModelerVueThemeSlot = "root" | "toolbar" | "diagnostics" | "tabs" | "workspace" | "design" | "palette" | "tree" | "canvas" | "preview" | "inspector" | "panel" | "editor" | "graph" | "graphNode" | "canvasBlock";
export type FormModelerVuePaletteItem =
  | { readonly id: string; readonly label: string; readonly category: string; readonly type: "field"; readonly valueKind: FormModelerField["valueKind"] }
  | { readonly id: string; readonly label: string; readonly category: string; readonly type: "element"; readonly elementKind: "group" | "horizontalLayout" | "verticalLayout" | "text" };

export const defaultFormModelerVuePalette: readonly FormModelerVuePaletteItem[] = Object.freeze([
  { id: "text-field", label: "Add text field", category: "Fields", type: "field", valueKind: "string" },
  { id: "number-field", label: "Add number field", category: "Fields", type: "field", valueKind: "number" },
  { id: "boolean-field", label: "Add yes/no field", category: "Fields", type: "field", valueKind: "boolean" },
  { id: "group", label: "Add group", category: "Layout", type: "element", elementKind: "group" },
  { id: "horizontal-layout", label: "Add horizontal layout", category: "Layout", type: "element", elementKind: "horizontalLayout" },
  { id: "vertical-layout", label: "Add vertical layout", category: "Layout", type: "element", elementKind: "verticalLayout" },
  { id: "text", label: "Add explanatory text", category: "Content", type: "element", elementKind: "text" }
]);

export interface ProgramKitFormModelerVueLabels {
  readonly undo: string; readonly redo: string; readonly commit: string; readonly applyJson: string;
  readonly design: string; readonly json: string; readonly graph: string; readonly structure: string;
  readonly inspector: string; readonly editor: string; readonly nodes: string; readonly relationships: string;
  readonly diagnostics: string; readonly palette: string; readonly canvas: string; readonly preview: string;
  readonly moveEarlier: string; readonly moveLater: string; readonly moveTo: string;
}

const defaultLabels: ProgramKitFormModelerVueLabels = Object.freeze({
  undo: "Undo", redo: "Redo", commit: "Commit changes", applyJson: "Apply JSON",
  design: "Design", json: "JSON", graph: "Graph", structure: "Form structure",
  inspector: "Properties", editor: "Form JSON", nodes: "Form nodes", relationships: "Relationships",
  diagnostics: "Modeler diagnostics", palette: "Component palette", canvas: "Layout canvas", preview: "Live preview",
  moveEarlier: "Move earlier", moveLater: "Move later", moveTo: "Move to"
});

function slot(name: FormModelerVueThemeSlot, defaultClass: string, classNames: ProgramKitClassNames<FormModelerVueThemeSlot>, unstyled: boolean, extra?: string) {
  return { class: programKitClassName(defaultClass, [classNames[name], extra].filter(Boolean).join(" ") || undefined, unstyled), "data-pk-slot": `form-modeler.${name}` };
}

export const ProgramKitFormJsonEditorVue = defineComponent({
  name: "ProgramKitFormJsonEditorVue",
  props: {
    source: { type: String, required: true }, accessibleLabel: { type: String, required: true },
    adapter: { type: Object as PropType<JsonEditorAdapter>, default: () => codeMirrorJsonEditorAdapter },
    mode: { type: String as PropType<FormModelerVueEditorMode>, default: "rich" }, cspNonce: { type: String, required: false },
    classNames: { type: Object as PropType<ProgramKitClassNames<FormModelerVueThemeSlot>>, default: () => ({}) }, unstyled: { type: Boolean, default: false }
  },
  emits: { change: (value: string) => typeof value === "string" },
  setup(props, { emit }) {
    const parent = ref<HTMLElement>(); let handle: JsonEditorHandle | undefined;
    const destroy = () => { handle?.destroy(); handle = undefined; };
    const mount = () => { destroy(); if (props.mode === "strictCsp" || parent.value === undefined) return; handle = props.adapter.mount({ parent: parent.value, document: props.source, accessibleLabel: props.accessibleLabel, onChange: value => emit("change", value), diagnostics: sourceDiagnostics, ...(props.cspNonce === undefined ? {} : { cspNonce: props.cspNonce }) }); };
    onMounted(mount); onBeforeUnmount(destroy);
    watch(() => [props.adapter, props.mode, props.accessibleLabel, props.cspNonce], mount);
    watch(() => props.source, value => handle?.setDocument(value));
    return () => props.mode === "strictCsp"
      ? h("textarea", { ...slot("editor", "pk-form-modeler__editor pk-form-modeler__editor--strict-csp", props.classNames, props.unstyled), "aria-label": props.accessibleLabel, value: props.source, spellcheck: false, onInput: (event: Event) => emit("change", (event.currentTarget as HTMLTextAreaElement).value) })
      : h("div", { ...slot("editor", "pk-form-modeler__editor", props.classNames, props.unstyled), ref: parent });
  }
});

export const ProgramKitFormModelerVue = defineComponent({
  name: "ProgramKitFormModelerVue",
  props: {
    session: { type: Object as PropType<FormModelerSession>, required: true }, initialView: { type: String as PropType<FormModelerVueView>, default: "design" },
    labels: { type: Object as PropType<Partial<ProgramKitFormModelerVueLabels>>, default: () => ({}) },
    actionCatalog: { type: Object as PropType<FormModelerActionCatalog>, required: false }, componentCatalog: { type: Object as PropType<FormModelerComponentCatalog>, required: false },
    paletteItems: { type: Array as unknown as PropType<readonly FormModelerVuePaletteItem[]>, default: () => defaultFormModelerVuePalette },
    renderPreview: { type: Function as PropType<(document: FormModelerDocument) => VNodeChild>, required: false },
    editorMode: { type: String as PropType<FormModelerVueEditorMode>, default: "rich" }, editorAdapter: { type: Object as PropType<JsonEditorAdapter>, default: () => codeMirrorJsonEditorAdapter }, cspNonce: { type: String, required: false },
    classNames: { type: Object as PropType<ProgramKitClassNames<FormModelerVueThemeSlot>>, default: () => ({}) }, className: { type: String, required: false }, unstyled: { type: Boolean, default: false }
  },
  emits: { change: (snapshot: FormModelerSnapshot) => snapshot !== null, commit: (document: FormModelerDocument, sequence: number) => document !== null && Number.isSafeInteger(sequence) },
  setup(props, { emit }) {
    const labels = computed(() => ({ ...defaultLabels, ...props.labels })); const view = ref<FormModelerVueView>(props.initialView);
    const snapshot = ref(props.session.snapshot()); const source = ref(serializeFormModelerDocument(snapshot.value.document)); const error = ref(""); const draggingId = ref<string>();
    const refresh = (next: FormModelerSnapshot) => { snapshot.value = next; source.value = serializeFormModelerDocument(next.document); error.value = ""; emit("change", next); };
    const apply = (operations: readonly FormModelerOperation[]): boolean => { try { refresh(props.session.apply({ commandId: `form-vue:${snapshot.value.sequence}:${counter++}`, expectedSequence: snapshot.value.sequence, operations })); return true; } catch (reason) { error.value = publicError(reason); return false; } };
    const select = (id: string) => refresh(props.session.select(id));
    const add = (item: FormModelerVuePaletteItem) => { const addition = createPaletteAddition(snapshot.value.document, snapshot.value.selectedId, item); if (apply(addition.operations)) select(addition.selectedId); };
    const applySource = () => { try { apply([{ type: "replaceDocument", document: parseFormModelerDocument(source.value) }]); } catch (reason) { error.value = publicError(reason); } };
    const bindingDiagnostics = computed(() => [...(props.actionCatalog?.validateBindings(snapshot.value.document.actions) ?? []), ...(props.componentCatalog?.validateBindings(snapshot.value.document.fields) ?? [])]);
    const tab = (target: FormModelerVueView, text: string) => h("button", { role: "tab", "aria-selected": view.value === target, tabindex: view.value === target ? 0 : -1, onClick: () => { view.value = target; }, type: "button" }, text);
    return () => h("section", { ...slot("root", "pk-form-modeler", props.classNames, props.unstyled, props.className), "data-pk-unstyled": props.unstyled || undefined, "data-view": view.value }, [
      h("div", { ...slot("toolbar", "pk-form-modeler__toolbar", props.classNames, props.unstyled), role: "toolbar", "aria-label": "Modeler actions" }, [
        h("button", { disabled: !snapshot.value.canUndo, onClick: () => refresh(props.session.undo()), type: "button" }, labels.value.undo),
        h("button", { disabled: !snapshot.value.canRedo, onClick: () => refresh(props.session.redo()), type: "button" }, labels.value.redo),
        h("button", { disabled: bindingDiagnostics.value.length > 0, onClick: () => emit("commit", snapshot.value.document, snapshot.value.sequence), type: "button" }, labels.value.commit)
      ]),
      bindingDiagnostics.value.length > 0 || error.value.length > 0 ? h("div", { ...slot("diagnostics", "pk-form-modeler__diagnostics", props.classNames, props.unstyled), role: "alert", "aria-label": labels.value.diagnostics }, [error.value.length > 0 ? h("p", error.value) : null, ...bindingDiagnostics.value.map(item => h("p", { key: `${item.code}-${item.path}` }, item.message))]) : null,
      h("div", { ...slot("tabs", "pk-form-modeler__tabs", props.classNames, props.unstyled), role: "tablist", "aria-label": "Modeler views" }, [tab("design", labels.value.design), tab("json", labels.value.json), tab("graph", labels.value.graph)]),
      view.value === "design" ? designView(snapshot.value, labels.value, props, draggingId, select, apply, add) : null,
      view.value === "json" ? h("section", { ...slot("panel", "pk-form-modeler__panel", props.classNames, props.unstyled), role: "tabpanel" }, [h(ProgramKitFormJsonEditorVue, { source: source.value, accessibleLabel: labels.value.editor, adapter: props.editorAdapter, mode: props.editorMode, classNames: props.classNames, unstyled: props.unstyled, ...(props.cspNonce === undefined ? {} : { cspNonce: props.cspNonce }), onChange: (value: string) => { source.value = value; } }), h("button", { onClick: applySource, type: "button" }, labels.value.applyJson)]) : null,
      view.value === "graph" ? graphView(snapshot.value, labels.value, props.classNames, props.unstyled, select) : null
    ]);
  }
});

function designView(snapshot: FormModelerSnapshot, labels: ProgramKitFormModelerVueLabels, props: { readonly paletteItems: readonly FormModelerVuePaletteItem[]; readonly renderPreview: ((document: FormModelerDocument) => VNodeChild) | undefined; readonly actionCatalog: FormModelerActionCatalog | undefined; readonly componentCatalog: FormModelerComponentCatalog | undefined; readonly classNames: ProgramKitClassNames<FormModelerVueThemeSlot>; readonly unstyled: boolean }, draggingId: { value: string | undefined }, select: (id: string) => void, apply: (operations: readonly FormModelerOperation[]) => void, add: (item: FormModelerVuePaletteItem) => void): VNode {
  const classNames = props.classNames; const unstyled = props.unstyled; const document = snapshot.document; const categories = [...new Set(props.paletteItems.map(item => item.category))];
  return h("section", slot("workspace", "pk-form-modeler__workspace", classNames, unstyled), [
    h("aside", { ...slot("palette", "pk-form-modeler__palette", classNames, unstyled), "aria-label": labels.palette }, [h("h2", labels.palette), ...categories.map(category => h("section", { key: category }, [h("h3", category), h("div", props.paletteItems.filter(item => item.category === category).map(item => h("button", { key: item.id, onClick: () => add(item), type: "button" }, item.label))) ]))]),
    h("div", slot("design", "pk-form-modeler__design", classNames, unstyled), [treeView(document, snapshot.selectedId, labels.structure, classNames, unstyled, select), canvasView(document, snapshot.selectedId, labels, classNames, unstyled, draggingId, select, apply), h("section", { ...slot("preview", "pk-form-modeler__preview", classNames, unstyled), "aria-label": labels.preview }, [h("h2", labels.preview), props.renderPreview?.(document) ?? h("p", `${document.fields.length} fields · ${countElements(document.layout)} layout blocks`)])]),
    inspectorView(document, snapshot.selectedId, labels, props.actionCatalog, props.componentCatalog, classNames, unstyled, apply)
  ]);
}

function treeView(document: FormModelerDocument, selectedId: string | undefined, label: string, classNames: ProgramKitClassNames<FormModelerVueThemeSlot>, unstyled: boolean, select: (id: string) => void): VNode {
  const button = (id: string, text: string) => h("li", { key: id }, [h("button", { "aria-current": selectedId === id, onClick: () => select(id), type: "button" }, text)]);
  const element = (value: FormModelerElement): VNode => h("li", { key: value.id }, [h("button", { "aria-current": selectedId === value.id, onClick: () => select(value.id), type: "button" }, `${value.id} · ${value.kind}`), ...(value.elements.length === 0 ? [] : [h("ul", value.elements.map(element))])]);
  return h("nav", { ...slot("tree", "pk-form-modeler__tree", classNames, unstyled), "aria-label": label }, [h("ul", [button(document.id, document.name), h("li", [h("span", "Fields"), h("ul", document.fields.map(field => button(field.id, field.label.defaultText)))]), h("li", [h("span", "Layout"), h("ul", [element(document.layout)])]), h("li", [h("span", "Actions"), h("ul", document.actions.map(action => button(action.id, action.label.defaultText)))])])]);
}

function canvasView(document: FormModelerDocument, selectedId: string | undefined, labels: ProgramKitFormModelerVueLabels, classNames: ProgramKitClassNames<FormModelerVueThemeSlot>, unstyled: boolean, draggingId: { value: string | undefined }, select: (id: string) => void, apply: (operations: readonly FormModelerOperation[]) => void): VNode {
  const fields = new Map(document.fields.map(field => [field.id, field]));
  const move = (elementId: string, parentId: string, index: number) => { const target = listFormModelerMoveTargets(document, elementId).find(item => item.parentId === parentId); if (target !== undefined && index >= 0 && index <= target.maximumIndex) apply([{ type: "moveElement", elementId, parentId, index }]); };
  const block = (element: FormModelerElement, index: number, siblings: number, parentId?: string): VNode => {
    const field = element.fieldId === undefined || element.fieldId === null ? undefined : fields.get(element.fieldId); const title = field?.label.defaultText ?? element.text?.defaultText ?? element.id; const movable = parentId !== undefined;
    return h("div", { ...slot("canvasBlock", "pk-form-modeler__canvas-block", classNames, unstyled), key: element.id, draggable: movable, "data-dragging": draggingId.value === element.id || undefined, "data-element-id": element.id, "data-kind": element.kind, onDragstart: (event: DragEvent) => { if (!movable) return; event.dataTransfer?.setData("application/x-program-kit-form-element", element.id); draggingId.value = element.id; }, onDragend: () => { draggingId.value = undefined; }, onDragover: (event: DragEvent) => { if (draggingId.value !== undefined && movable) event.preventDefault(); }, onDrop: (event: DragEvent) => { if (draggingId.value === undefined || parentId === undefined || draggingId.value === element.id) return; event.preventDefault(); move(draggingId.value, parentId, index); draggingId.value = undefined; } }, [
      h("div", { class: "pk-form-modeler__canvas-heading" }, [h("button", { "aria-pressed": selectedId === element.id, onClick: () => select(element.id), onKeydown: (event: KeyboardEvent) => { if (!event.altKey || parentId === undefined) return; if (event.key === "ArrowUp" && index > 0) { event.preventDefault(); move(element.id, parentId, index - 1); } if (event.key === "ArrowDown" && index < siblings - 1) { event.preventDefault(); move(element.id, parentId, index + 1); } }, type: "button" }, [h("strong", title), h("small", element.kind)]), movable ? h("div", { class: "pk-form-modeler__reorder", role: "group", "aria-label": `Reorder ${title}` }, [h("button", { "aria-label": `${labels.moveEarlier}: ${title}`, disabled: index === 0, onClick: () => move(element.id, parentId, index - 1), type: "button" }, "↑"), h("button", { "aria-label": `${labels.moveLater}: ${title}`, disabled: index >= siblings - 1, onClick: () => move(element.id, parentId, index + 1), type: "button" }, "↓")]) : null]),
      containerKinds.has(element.kind) ? h("div", { class: "pk-form-modeler__canvas-children", "data-drop-parent": element.id, onDragover: (event: DragEvent) => { if (draggingId.value !== undefined && draggingId.value !== element.id) event.preventDefault(); }, onDrop: (event: DragEvent) => { if (draggingId.value === undefined || draggingId.value === element.id) return; event.preventDefault(); move(draggingId.value, element.id, element.elements.length); draggingId.value = undefined; } }, element.elements.length === 0 ? [h("span", { class: "pk-form-modeler__empty-drop", "aria-hidden": "true" }, "Drop components here")] : element.elements.map((child, childIndex) => block(child, childIndex, element.elements.length, element.id))) : null
    ]);
  };
  return h("section", { ...slot("canvas", "pk-form-modeler__canvas", classNames, unstyled), "aria-label": labels.canvas }, [h("h2", labels.canvas), block(document.layout, 0, 1)]);
}

function inspectorView(document: FormModelerDocument, selectedId: string | undefined, labels: ProgramKitFormModelerVueLabels, actionCatalog: FormModelerActionCatalog | undefined, componentCatalog: FormModelerComponentCatalog | undefined, classNames: ProgramKitClassNames<FormModelerVueThemeSlot>, unstyled: boolean, apply: (operations: readonly FormModelerOperation[]) => void): VNode {
  const entity = findEntity(document, selectedId ?? document.id); const root = (children: VNodeChild[]) => h("aside", { ...slot("inspector", "pk-form-modeler__inspector", classNames, unstyled), "aria-label": labels.inspector }, children);
  if (entity.kind === "field") { const field = entity.value; const update = (changes: Partial<FormModelerField>) => apply([{ type: "upsertField", field: { ...field, ...changes } }]); const available = componentCatalog?.listFor(field.valueKind) ?? []; const contract = field.component == null ? undefined : componentCatalog?.resolve(field.component.componentId); return root([h("h2", field.id), h("label", { class: "pk-form-modeler__field" }, ["Label", h("input", { value: field.label.defaultText, onChange: (event: Event) => update({ label: { ...field.label, defaultText: (event.currentTarget as HTMLInputElement).value } }) })]), h("label", [h("input", { type: "checkbox", checked: field.required, onChange: (event: Event) => update({ required: (event.currentTarget as HTMLInputElement).checked }) }), " Required"]), componentCatalog === undefined ? null : h("label", { class: "pk-form-modeler__field" }, ["Component", h("select", { value: field.component?.componentId ?? "", onChange: (event: Event) => { const value = (event.currentTarget as HTMLSelectElement).value; update({ component: value.length === 0 ? null : componentCatalog.createReference(value) }); } }, [h("option", { value: "" }, "Default renderer"), ...available.map(item => h("option", { key: item.componentId, value: item.componentId }, item.displayName))])]), contract === undefined ? null : componentEditor(field, contract, update), h("dl", [h("dt", "Data path"), h("dd", field.dataPath), h("dt", "Value kind"), h("dd", field.valueKind)])]); }
  if (entity.kind === "action") { const contract = actionCatalog?.resolve(entity.value.handlerId); return root([h("h2", entity.value.label.defaultText), h("dl", [h("dt", "Handler"), h("dd", entity.value.handlerId), h("dt", "Execution"), h("dd", contract?.execution ?? "Unregistered"), h("dt", "Package"), h("dd", contract?.providerPackage ?? "Application-owned")])]); }
  if (entity.kind === "element") { const placement = getFormModelerElementPlacement(document, entity.value.id); const targets = listFormModelerMoveTargets(document, entity.value.id); return root([h("h2", entity.value.id), h("dl", [h("dt", "Kind"), h("dd", entity.value.kind), h("dt", "Children"), h("dd", String(entity.value.elements.length))]), placement.parentId === undefined ? null : h("fieldset", { class: "pk-form-modeler__move" }, [h("legend", labels.moveTo), ...targets.map(target => h("button", { disabled: target.parentId === placement.parentId, onClick: () => apply([{ type: "moveElement", elementId: entity.value.id, parentId: target.parentId, index: target.maximumIndex }]), type: "button" }, target.label))])]); }
  return root([h("h2", document.name), h("dl", [h("dt", "ID"), h("dd", document.id), h("dt", "Revision"), h("dd", String(document.revision)), h("dt", "Source locale"), h("dd", document.sourceLocale)])]);
}

function graphView(snapshot: FormModelerSnapshot, labels: ProgramKitFormModelerVueLabels, classNames: ProgramKitClassNames<FormModelerVueThemeSlot>, unstyled: boolean, select: (id: string) => void): VNode { const graph = projectFormModelerGraph(snapshot.document); return h("section", { ...slot("graph", "pk-form-modeler__panel", classNames, unstyled), role: "tabpanel" }, [h("h2", labels.nodes), h("div", { class: "pk-form-modeler__graph-nodes" }, graph.nodes.map(node => { const id = node.id.slice(node.id.indexOf(":") + 1); return h("button", { ...slot("graphNode", "pk-form-modeler__graph-node", classNames, unstyled), "aria-pressed": snapshot.selectedId === id, onClick: () => select(id), type: "button" }, [h("strong", node.label), h("small", node.kind)]); })), h("h2", labels.relationships), h("table", { class: "pk-form-modeler__graph-edges" }, [h("thead", [h("tr", [h("th", "From"), h("th", "Relationship"), h("th", "To")])]), h("tbody", graph.edges.map(edge => h("tr", [h("td", edge.from), h("td", edge.kind), h("td", edge.to)])))])]); }

function componentEditor(field: FormModelerField, contract: FormModelerComponentContract, update: (changes: Partial<FormModelerField>) => void): VNode {
  const updateOption = (key: string, value: string) => { if (field.component != null) update({ component: { ...field.component, options: { ...field.component.options, [key]: value } } }); };
  return h("div", { class: "pk-form-modeler__component" }, [
    h("p", contract.description ?? contract.displayName),
    h("dl", [h("dt", "Package"), h("dd", contract.providerPackage ?? "Application-owned"), h("dt", "Compatible version"), h("dd", contract.versionRange)]),
    ...(contract.options ?? []).map(option => h("label", { class: "pk-form-modeler__field", key: option.key }, [
      option.displayName,
      option.kind === "choice" || option.kind === "boolean"
        ? h("select", { value: field.component?.options?.[option.key] ?? option.defaultValue ?? "", required: option.required, onChange: (event: Event) => updateOption(option.key, (event.currentTarget as HTMLSelectElement).value) }, [h("option", { value: "", disabled: option.required }, "Select"), ...(option.kind === "boolean" ? [{ value: "true", label: "Yes" }, { value: "false", label: "No" }] : option.choices ?? []).map(choice => h("option", { value: choice.value, key: choice.value }, choice.label))])
        : h("input", { value: field.component?.options?.[option.key] ?? option.defaultValue ?? "", required: option.required, inputmode: option.kind === "integer" ? "numeric" : undefined, onInput: (event: Event) => updateOption(option.key, (event.currentTarget as HTMLInputElement).value) })
    ]))
  ]);
}

function sourceDiagnostics(source: string): readonly JsonEditorDiagnostic[] { try { parseFormModelerDocument(source); return []; } catch (error) { return [{ from: 0, to: source.length, severity: "error", message: publicError(error) }]; } }
function publicError(error: unknown): string { return error instanceof Error ? error.message : "The form operation could not be completed."; }
type Entity = { readonly kind: "form"; readonly value: FormModelerDocument } | { readonly kind: "field"; readonly value: FormModelerField } | { readonly kind: "action"; readonly value: FormModelerAction } | { readonly kind: "element"; readonly value: FormModelerElement };
function findEntity(document: FormModelerDocument, id: string): Entity { if (document.id === id) return { kind: "form", value: document }; const field = document.fields.find(item => item.id === id); if (field !== undefined) return { kind: "field", value: field }; const action = document.actions.find(item => item.id === id); if (action !== undefined) return { kind: "action", value: action }; const element = findElement(document.layout, id); return element === undefined ? { kind: "form", value: document } : { kind: "element", value: element }; }
function findElement(element: FormModelerElement, id: string): FormModelerElement | undefined { if (element.id === id) return element; for (const child of element.elements) { const value = findElement(child, id); if (value !== undefined) return value; } return undefined; }
function createPaletteAddition(document: FormModelerDocument, selectedId: string | undefined, item: FormModelerVuePaletteItem): { readonly operations: readonly FormModelerOperation[]; readonly selectedId: string } { const selected = selectedId === undefined ? undefined : findElement(document.layout, selectedId); const parentId = selected !== undefined && containerKinds.has(selected.kind) ? selected.id : document.layout.id; const index = findElement(document.layout, parentId)?.elements.length ?? 0; if (item.type === "field") { const fieldId = nextId(document, "field"); const field: FormModelerField = { id: fieldId, dataPath: `/${fieldId}`, valueKind: item.valueKind, required: false, label: { key: `fields.${fieldId}`, defaultText: `Field ${fieldId.slice(6)}` } }; const controlId = nextId(document, `${fieldId}-control`); return { operations: [{ type: "upsertField", field }, { type: "insertElement", parentId, index, element: { id: controlId, kind: "control", fieldId, elements: [] } }], selectedId: fieldId }; } const prefix = item.elementKind.replace(/[A-Z]/g, value => `-${value.toLowerCase()}`); const id = nextId(document, prefix); return { operations: [{ type: "insertElement", parentId, index, element: { id, kind: item.elementKind, elements: [], ...(item.elementKind === "text" ? { text: { key: `content.${id}`, defaultText: "Explanatory text" } } : {}) } }], selectedId: id }; }
function nextId(document: FormModelerDocument, prefix: string): string { const ids = new Set([document.id, ...document.fields.map(item => item.id), ...document.actions.map(item => item.id)]); const visit = (element: FormModelerElement) => { ids.add(element.id); element.elements.forEach(visit); }; visit(document.layout); let value = 1; while (ids.has(`${prefix}-${value}`)) value += 1; return `${prefix}-${value}`; }
function countElements(element: FormModelerElement): number { return 1 + element.elements.reduce((total, child) => total + countElements(child), 0); }
const containerKinds = new Set<FormModelerElement["kind"]>(["group", "horizontalLayout", "verticalLayout", "wizard", "step"]);
let counter = 1;
