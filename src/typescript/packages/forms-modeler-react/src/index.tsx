import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { mountJsonEditor, type JsonEditorDiagnostic, type JsonEditorHandle } from "@orbyss/program-kit-forms-codemirror";
import {
  FormModelerSession,
  parseFormModelerDocument,
  projectFormModelerGraph,
  serializeFormModelerDocument,
  type FormModelerAction,
  type FormModelerActionCatalog,
  type FormModelerComponentCatalog,
  type FormModelerDocument,
  type FormModelerElement,
  type FormModelerField,
  type FormModelerOperation,
  type FormModelerSnapshot
} from "@orbyss/program-kit-forms-modeler";

export type FormModelerView = "design" | "json" | "graph";
export type FormModelerEditorMode = "codemirror" | "strictCsp";
export type FormModelerPaletteItem =
  | { readonly id: string; readonly label: string; readonly category: string; readonly type: "field"; readonly valueKind: FormModelerField["valueKind"] }
  | { readonly id: string; readonly label: string; readonly category: string; readonly type: "element"; readonly elementKind: "group" | "horizontalLayout" | "verticalLayout" | "text" };

export const defaultFormModelerPalette: readonly FormModelerPaletteItem[] = Object.freeze([
  { id: "text-field", label: "Add text field", category: "Fields", type: "field", valueKind: "string" },
  { id: "number-field", label: "Add number field", category: "Fields", type: "field", valueKind: "number" },
  { id: "boolean-field", label: "Add yes/no field", category: "Fields", type: "field", valueKind: "boolean" },
  { id: "group", label: "Add group", category: "Layout", type: "element", elementKind: "group" },
  { id: "horizontal-layout", label: "Add horizontal layout", category: "Layout", type: "element", elementKind: "horizontalLayout" },
  { id: "vertical-layout", label: "Add vertical layout", category: "Layout", type: "element", elementKind: "verticalLayout" },
  { id: "text", label: "Add explanatory text", category: "Content", type: "element", elementKind: "text" }
]);

export interface ProgramKitFormModelerLabels {
  readonly undo: string;
  readonly redo: string;
  readonly commit: string;
  readonly applyJson: string;
  readonly design: string;
  readonly json: string;
  readonly graph: string;
  readonly structure: string;
  readonly inspector: string;
  readonly editor: string;
  readonly nodes: string;
  readonly relationships: string;
  readonly diagnostics: string;
  readonly palette: string;
  readonly canvas: string;
  readonly preview: string;
}

export interface ProgramKitFormModelerProps {
  readonly session: FormModelerSession;
  readonly initialView?: FormModelerView;
  readonly labels?: Partial<ProgramKitFormModelerLabels>;
  readonly actionCatalog?: FormModelerActionCatalog;
  readonly componentCatalog?: FormModelerComponentCatalog;
  readonly paletteItems?: readonly FormModelerPaletteItem[];
  /** Trusted application renderer; preview code never comes from the form document. */
  readonly renderPreview?: (document: FormModelerDocument) => ReactNode;
  /** CodeMirror is the default. Use strictCsp when style attributes are prohibited by policy. */
  readonly editorMode?: FormModelerEditorMode;
  /** Nonce for CodeMirror's generated stylesheet; it does not authorize runtime style attributes. */
  readonly cspNonce?: string;
  readonly onChange?: (snapshot: FormModelerSnapshot) => void;
  readonly onCommit?: (document: FormModelerDocument, sequence: number) => void | Promise<void>;
}

const defaults: ProgramKitFormModelerLabels = Object.freeze({
  undo: "Undo", redo: "Redo", commit: "Commit changes", applyJson: "Apply JSON",
  design: "Design", json: "JSON", graph: "Graph", structure: "Form structure",
  inspector: "Properties", editor: "Form JSON", nodes: "Form nodes", relationships: "Relationships",
  diagnostics: "Modeler diagnostics", palette: "Component palette", canvas: "Layout canvas", preview: "Live preview"
});

export function ProgramKitFormModeler({ session, initialView = "design", labels: overrides, actionCatalog, componentCatalog, paletteItems = defaultFormModelerPalette, renderPreview, editorMode = "codemirror", cspNonce, onChange, onCommit }: ProgramKitFormModelerProps): ReactNode {
  const instanceId = useId();
  const labels = { ...defaults, ...overrides };
  const [view, setView] = useState<FormModelerView>(initialView);
  const [snapshot, setSnapshot] = useState(() => session.snapshot());
  const [source, setSource] = useState(() => serializeFormModelerDocument(snapshot.document));
  const [sourceError, setSourceError] = useState("");
  const bindingDiagnostics = [
    ...(actionCatalog?.validateBindings(snapshot.document.actions) ?? []),
    ...(componentCatalog?.validateBindings(snapshot.document.fields) ?? [])
  ];
  const commandSequence = useRef(0);
  const refresh = (next: FormModelerSnapshot) => {
    setSnapshot(next);
    setSource(serializeFormModelerDocument(next.document));
    setSourceError("");
    onChange?.(next);
  };
  const apply = (operations: readonly FormModelerOperation[]) => refresh(session.apply({
    commandId: `modeler-${snapshot.sequence}-${++commandSequence.current}`,
    expectedSequence: snapshot.sequence,
    operations
  }));
  const addPaletteItem = (item: FormModelerPaletteItem) => {
    const addition = createPaletteAddition(snapshot.document, snapshot.selectedId, item);
    apply(addition.operations);
    refreshSelection(session.select(addition.selectedId), setSnapshot, onChange);
  };
  const select = (id: string) => refreshSelection(session.select(id), setSnapshot, onChange);
  const applySource = () => {
    try {
      const document = parseFormModelerDocument(source);
      apply([{ type: "replaceDocument", document }]);
    } catch (error) {
      setSourceError(error instanceof Error ? error.message : "The JSON document is invalid.");
    }
  };

  return (
    <section className="pk-form-modeler" data-view={view}>
      <div aria-label="Modeler actions" className="pk-form-modeler__toolbar" role="toolbar">
        <button disabled={!snapshot.canUndo} onClick={() => refresh(session.undo())} type="button">{labels.undo}</button>
        <button disabled={!snapshot.canRedo} onClick={() => refresh(session.redo())} type="button">{labels.redo}</button>
        {onCommit !== undefined && <button disabled={bindingDiagnostics.length > 0} onClick={() => { void onCommit(snapshot.document, snapshot.sequence); }} type="button">{labels.commit}</button>}
      </div>
      {bindingDiagnostics.length > 0 && <div aria-label={labels.diagnostics} className="pk-form-modeler__diagnostics" role="alert"><ul>{bindingDiagnostics.map(diagnostic => <li key={`${diagnostic.code}-${diagnostic.path}`}>{diagnostic.message}</li>)}</ul></div>}
      <div aria-label="Modeler views" className="pk-form-modeler__tabs" role="tablist">
        {(["design", "json", "graph"] as const).map(candidate => (
          <button aria-controls={`${instanceId}-${candidate}-panel`} aria-selected={view === candidate} id={`${instanceId}-${candidate}-tab`} key={candidate} onClick={() => setView(candidate)} role="tab" type="button">
            {labels[candidate]}
          </button>
        ))}
      </div>
      {view === "design" && (
        <div aria-labelledby={`${instanceId}-design-tab`} className="pk-form-modeler__workspace" id={`${instanceId}-design-panel`} role="tabpanel">
          <FormModelerPalette items={paletteItems} label={labels.palette} onAdd={addPaletteItem} />
          <div className="pk-form-modeler__design">
            <FormModelerTree document={snapshot.document} label={labels.structure} onSelect={select} selectedId={snapshot.selectedId} />
            <FormModelerCanvas document={snapshot.document} label={labels.canvas} onSelect={select} selectedId={snapshot.selectedId} />
            <section aria-label={labels.preview} className="pk-form-modeler__preview"><h2>{labels.preview}</h2>{renderPreview?.(snapshot.document) ?? <p>{snapshot.document.fields.length} fields · {countElements(snapshot.document.layout)} layout blocks</p>}</section>
          </div>
          <FormModelerInspector actionCatalog={actionCatalog} componentCatalog={componentCatalog} document={snapshot.document} label={labels.inspector} onApply={apply} selectedId={snapshot.selectedId} />
        </div>
      )}
      {view === "json" && (
        <div aria-labelledby={`${instanceId}-json-tab`} className="pk-form-modeler__panel" id={`${instanceId}-json-panel`} role="tabpanel">
          <FormModelerJsonEditor accessibleLabel={labels.editor} {...(cspNonce === undefined ? {} : { cspNonce })} mode={editorMode} onChange={setSource} source={source} />
          <button onClick={applySource} type="button">{labels.applyJson}</button>
          {sourceError.length > 0 && <pre className="pk-form-modeler__error" role="alert">{sourceError}</pre>}
        </div>
      )}
      {view === "graph" && <FormModelerGraph document={snapshot.document} labelledBy={`${instanceId}-graph-tab`} labels={labels} onSelect={select} panelId={`${instanceId}-graph-panel`} selectedId={snapshot.selectedId} />}
    </section>
  );
}

export function FormModelerPalette({ items, label, onAdd }: { readonly items: readonly FormModelerPaletteItem[]; readonly label: string; readonly onAdd: (item: FormModelerPaletteItem) => void }): ReactNode {
  const categories = [...new Set(items.map(item => item.category))];
  return <aside aria-label={label} className="pk-form-modeler__palette"><h2>{label}</h2>{categories.map(category => <section key={category}><h3>{category}</h3><div>{items.filter(item => item.category === category).map(item => <button key={item.id} onClick={() => onAdd(item)} type="button">{item.label}</button>)}</div></section>)}</aside>;
}

export function FormModelerCanvas({ document, label, selectedId, onSelect }: { readonly document: FormModelerDocument; readonly label: string; readonly selectedId: string | undefined; readonly onSelect: (id: string) => void }): ReactNode {
  const fields = new Map(document.fields.map(field => [field.id, field]));
  return <section aria-label={label} className="pk-form-modeler__canvas"><h2>{label}</h2><CanvasElement element={document.layout} fields={fields} onSelect={onSelect} selectedId={selectedId} /></section>;
}

function CanvasElement({ element, fields, selectedId, onSelect }: { readonly element: FormModelerElement; readonly fields: ReadonlyMap<string, FormModelerField>; readonly selectedId: string | undefined; readonly onSelect: (id: string) => void }): ReactNode {
  const field = element.fieldId === undefined || element.fieldId === null ? undefined : fields.get(element.fieldId);
  return <div className="pk-form-modeler__canvas-block" data-kind={element.kind}><button aria-pressed={selectedId === element.id} onClick={() => onSelect(element.id)} type="button"><strong>{field?.label.defaultText ?? element.text?.defaultText ?? element.id}</strong><small>{element.kind}</small></button>{element.elements.length > 0 && <div className="pk-form-modeler__canvas-children">{element.elements.map(child => <CanvasElement element={child} fields={fields} key={child.id} onSelect={onSelect} selectedId={selectedId} />)}</div>}</div>;
}

export interface FormModelerTreeProps { readonly document: FormModelerDocument; readonly label: string; readonly selectedId: string | undefined; readonly onSelect: (id: string) => void; }
export function FormModelerTree({ document, label, selectedId, onSelect }: FormModelerTreeProps): ReactNode {
  return <nav aria-label={label} className="pk-form-modeler__tree"><ul>
    <TreeButton id={document.id} label={document.name} selectedId={selectedId} onSelect={onSelect} />
    <li><span>Fields</span><ul>{document.fields.map(field => <TreeButton id={field.id} key={field.id} label={field.label.defaultText} selectedId={selectedId} onSelect={onSelect} />)}</ul></li>
    <li><span>Layout</span><ElementTree element={document.layout} selectedId={selectedId} onSelect={onSelect} /></li>
    <li><span>Actions</span><ul>{document.actions.map(action => <TreeButton id={action.id} key={action.id} label={action.label.defaultText} selectedId={selectedId} onSelect={onSelect} />)}</ul></li>
  </ul></nav>;
}

function ElementTree({ element, selectedId, onSelect }: { readonly element: FormModelerElement; readonly selectedId: string | undefined; readonly onSelect: (id: string) => void }): ReactNode {
  return <ul><TreeButton id={element.id} label={`${element.id} · ${element.kind}`} selectedId={selectedId} onSelect={onSelect} />{element.elements.map(child => <li key={child.id}><ElementTree element={child} selectedId={selectedId} onSelect={onSelect} /></li>)}</ul>;
}
function TreeButton({ id, label, selectedId, onSelect }: { readonly id: string; readonly label: string; readonly selectedId: string | undefined; readonly onSelect: (id: string) => void }): ReactNode {
  return <li><button aria-current={selectedId === id} onClick={() => onSelect(id)} type="button">{label}</button></li>;
}

interface InspectorProps { readonly document: FormModelerDocument; readonly selectedId: string | undefined; readonly label: string; readonly actionCatalog: FormModelerActionCatalog | undefined; readonly componentCatalog: FormModelerComponentCatalog | undefined; readonly onApply: (operations: readonly FormModelerOperation[]) => void; }
export function FormModelerInspector({ document, selectedId, label, actionCatalog, componentCatalog, onApply }: InspectorProps): ReactNode {
  const entity = findEntity(document, selectedId ?? document.id);
  if (entity.kind === "field") return <FieldInspector componentCatalog={componentCatalog} field={entity.value} label={label} onApply={onApply} />;
  if (entity.kind === "action") {
    const contract = actionCatalog?.resolve(entity.value.handlerId);
    return <aside aria-label={label} className="pk-form-modeler__inspector"><h2>{entity.value.label.defaultText}</h2><dl><dt>Handler</dt><dd>{entity.value.handlerId}</dd><dt>Execution</dt><dd>{contract?.execution ?? "Unregistered"}</dd><dt>Package</dt><dd>{contract?.providerPackage ?? "Application-owned"}</dd></dl></aside>;
  }
  if (entity.kind === "element") return <aside aria-label={label} className="pk-form-modeler__inspector"><h2>{entity.value.id}</h2><dl><dt>Kind</dt><dd>{entity.value.kind}</dd><dt>Children</dt><dd>{entity.value.elements.length}</dd></dl></aside>;
  return <aside aria-label={label} className="pk-form-modeler__inspector"><h2>{document.name}</h2><dl><dt>ID</dt><dd>{document.id}</dd><dt>Revision</dt><dd>{document.revision}</dd><dt>Source locale</dt><dd>{document.sourceLocale}</dd></dl></aside>;
}

function FieldInspector({ field, label, componentCatalog, onApply }: { readonly field: FormModelerField; readonly label: string; readonly componentCatalog: FormModelerComponentCatalog | undefined; readonly onApply: (operations: readonly FormModelerOperation[]) => void }): ReactNode {
  const [text, setText] = useState(field.label.defaultText);
  useEffect(() => setText(field.label.defaultText), [field]);
  const update = (changes: Partial<FormModelerField>) => onApply([{ type: "upsertField", field: { ...field, ...changes } }]);
  const availableComponents = componentCatalog?.listFor(field.valueKind) ?? [];
  const selectedContract = field.component === undefined || field.component === null ? undefined : componentCatalog?.resolve(field.component.componentId);
  const updateOption = (key: string, value: string) => {
    if (field.component === undefined || field.component === null) return;
    update({ component: { ...field.component, options: { ...field.component.options, [key]: value } } });
  };
  return <aside aria-label={label} className="pk-form-modeler__inspector"><h2>{field.id}</h2>
    <label className="pk-form-modeler__field">Label<input onChange={event => setText(event.currentTarget.value)} onBlur={() => { if (text !== field.label.defaultText) update({ label: { ...field.label, defaultText: text } }); }} value={text} /></label>
    <label><input checked={field.required} onChange={event => update({ required: event.currentTarget.checked })} type="checkbox" /> Required</label>
    {componentCatalog !== undefined && <label className="pk-form-modeler__field">Component<select onChange={event => update({ component: event.currentTarget.value.length === 0 ? null : componentCatalog.createReference(event.currentTarget.value) })} value={field.component?.componentId ?? ""}><option value="">Default renderer</option>{availableComponents.map(contract => <option key={contract.componentId} value={contract.componentId}>{contract.displayName}</option>)}</select></label>}
    {selectedContract !== undefined && <div className="pk-form-modeler__component"><p>{selectedContract.description ?? selectedContract.displayName}</p><dl><dt>Package</dt><dd>{selectedContract.providerPackage ?? "Application-owned"}</dd><dt>Compatible version</dt><dd>{selectedContract.versionRange}</dd></dl>{(selectedContract.options ?? []).map(option => <label className="pk-form-modeler__field" key={option.key}>{option.displayName}{option.kind === "choice" || option.kind === "boolean" ? <select onChange={event => updateOption(option.key, event.currentTarget.value)} required={option.required} value={field.component?.options?.[option.key] ?? option.defaultValue ?? ""}><option disabled={option.required} value="">Select</option>{(option.kind === "boolean" ? [{ value: "true", label: "Yes" }, { value: "false", label: "No" }] : option.choices ?? []).map(choice => <option key={choice.value} value={choice.value}>{choice.label}</option>)}</select> : <input inputMode={option.kind === "integer" ? "numeric" : undefined} onChange={event => updateOption(option.key, event.currentTarget.value)} required={option.required} value={field.component?.options?.[option.key] ?? option.defaultValue ?? ""} />}</label>)}</div>}
    <dl><dt>Data path</dt><dd>{field.dataPath}</dd><dt>Value kind</dt><dd>{field.valueKind}</dd></dl>
  </aside>;
}

export function FormModelerJsonEditor({ source, accessibleLabel, cspNonce, mode, onChange }: { readonly source: string; readonly accessibleLabel: string; readonly cspNonce?: string; readonly mode: FormModelerEditorMode; readonly onChange: (source: string) => void }): ReactNode {
  const parent = useRef<HTMLDivElement>(null);
  const handle = useRef<JsonEditorHandle | null>(null);
  useEffect(() => {
    if (mode === "strictCsp") return;
    if (parent.current === null) return;
    handle.current = mountJsonEditor({ parent: parent.current, document: source, accessibleLabel, onChange, diagnostics: sourceDiagnostics, ...(cspNonce === undefined ? {} : { cspNonce }) });
    return () => { handle.current?.destroy(); handle.current = null; };
  }, [accessibleLabel, cspNonce, mode, onChange]);
  useEffect(() => handle.current?.setDocument(source), [source]);
  if (mode === "strictCsp") {
    return <textarea aria-label={accessibleLabel} className="pk-form-modeler__editor pk-form-modeler__editor--strict-csp" onChange={event => onChange(event.currentTarget.value)} spellCheck={false} value={source} />;
  }
  return <div className="pk-form-modeler__editor" ref={parent} />;
}

export function FormModelerGraph({ document, labels, labelledBy, panelId, selectedId, onSelect }: { readonly document: FormModelerDocument; readonly labels: ProgramKitFormModelerLabels; readonly labelledBy?: string; readonly panelId?: string; readonly selectedId: string | undefined; readonly onSelect: (id: string) => void }): ReactNode {
  const graph = useMemo(() => projectFormModelerGraph(document), [document]);
  return <section aria-labelledby={labelledBy} className="pk-form-modeler__panel" id={panelId} role="tabpanel"><h2>{labels.nodes}</h2><div className="pk-form-modeler__graph-nodes">{graph.nodes.map(node => {
    const rawId = node.id.slice(node.id.indexOf(":") + 1);
    return <button aria-pressed={selectedId === rawId} className="pk-form-modeler__graph-node" key={node.id} onClick={() => onSelect(rawId)} type="button"><strong>{node.label}</strong><small>{node.kind}</small></button>;
  })}</div><h2>{labels.relationships}</h2><table className="pk-form-modeler__graph-edges"><thead><tr><th>From</th><th>Relationship</th><th>To</th></tr></thead><tbody>{graph.edges.map((edge, index) => <tr key={`${edge.from}-${edge.to}-${index}`}><td>{edge.from}</td><td>{edge.kind}</td><td>{edge.to}</td></tr>)}</tbody></table></section>;
}

function sourceDiagnostics(source: string): readonly JsonEditorDiagnostic[] {
  try { parseFormModelerDocument(source); return []; }
  catch (error) { return [{ from: 0, to: Math.max(0, source.length), severity: "error", message: error instanceof Error ? error.message : "Invalid modeler document." }]; }
}

type Entity = { readonly kind: "form"; readonly value: FormModelerDocument } | { readonly kind: "field"; readonly value: FormModelerField } | { readonly kind: "action"; readonly value: FormModelerAction } | { readonly kind: "element"; readonly value: FormModelerElement };
function findEntity(document: FormModelerDocument, id: string): Entity {
  if (document.id === id) return { kind: "form", value: document };
  const field = document.fields.find(item => item.id === id); if (field !== undefined) return { kind: "field", value: field };
  const action = document.actions.find(item => item.id === id); if (action !== undefined) return { kind: "action", value: action };
  const element = findElement(document.layout, id); return element === undefined ? { kind: "form", value: document } : { kind: "element", value: element };
}
function findElement(element: FormModelerElement, id: string): FormModelerElement | undefined { if (element.id === id) return element; for (const child of element.elements) { const match = findElement(child, id); if (match !== undefined) return match; } return undefined; }
function refreshSelection(snapshot: FormModelerSnapshot, setSnapshot: (snapshot: FormModelerSnapshot) => void, onChange?: (snapshot: FormModelerSnapshot) => void): void { setSnapshot(snapshot); onChange?.(snapshot); }

function createPaletteAddition(document: FormModelerDocument, selectedId: string | undefined, item: FormModelerPaletteItem): { readonly operations: readonly FormModelerOperation[]; readonly selectedId: string } {
  const selectedElement = selectedId === undefined ? undefined : findElement(document.layout, selectedId);
  const parentId = selectedElement !== undefined && containerKinds.has(selectedElement.kind) ? selectedElement.id : document.layout.id;
  const insertionIndex = (findElement(document.layout, parentId)?.elements.length) ?? 0;
  if (item.type === "field") {
    const fieldId = nextDocumentId(document, "field");
    const field: FormModelerField = {
      id: fieldId,
      dataPath: `/${fieldId}`,
      valueKind: item.valueKind,
      required: false,
      label: { key: `fields.${fieldId}`, defaultText: `Field ${fieldId.slice("field-".length)}` }
    };
    const controlId = nextDocumentId(document, `${fieldId}-control`);
    return {
      operations: [
        { type: "upsertField", field },
        { type: "insertElement", parentId, index: insertionIndex, element: { id: controlId, kind: "control", fieldId, elements: [] } }
      ],
      selectedId: fieldId
    };
  }
  const prefix = item.elementKind.replace(/[A-Z]/g, match => `-${match.toLowerCase()}`);
  const elementId = nextDocumentId(document, prefix);
  const element: FormModelerElement = {
    id: elementId,
    kind: item.elementKind,
    elements: [],
    ...(item.elementKind === "text" ? { text: { key: `content.${elementId}`, defaultText: "Explanatory text" } } : {})
  };
  return { operations: [{ type: "insertElement", parentId, index: insertionIndex, element }], selectedId: elementId };
}

const containerKinds = new Set<FormModelerElement["kind"]>(["group", "horizontalLayout", "verticalLayout", "wizard", "step"]);

function nextDocumentId(document: FormModelerDocument, prefix: string): string {
  const ids = new Set<string>([document.id, ...document.fields.map(field => field.id), ...document.actions.map(action => action.id)]);
  const visit = (element: FormModelerElement) => { ids.add(element.id); element.elements.forEach(visit); };
  visit(document.layout);
  let number = 1;
  while (ids.has(`${prefix}-${number}`)) number += 1;
  return `${prefix}-${number}`;
}

function countElements(element: FormModelerElement): number {
  return 1 + element.elements.reduce((count, child) => count + countElements(child), 0);
}
