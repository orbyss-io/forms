import { createContext, useContext, useEffect, useId, useRef, useState, type ReactNode } from "react";
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

export type SchemaModelerView = "design" | "json" | "graph";
export type SchemaModelerEditorMode = "rich" | "strictCsp";
export type SchemaModelerThemeSlot = "root" | "toolbar" | "diagnostics" | "tabs" | "workspace" | "palette" | "tree" | "canvas" | "canvasBlock" | "inspector" | "editor" | "graph" | "graphNode";

export interface ProgramKitSchemaModelerLabels {
  readonly undo: string; readonly redo: string; readonly commit: string; readonly applyJson: string;
  readonly design: string; readonly json: string; readonly graph: string; readonly palette: string;
  readonly structure: string; readonly canvas: string; readonly inspector: string; readonly editor: string;
  readonly diagnostics: string; readonly remove: string;
}

export interface ProgramKitSchemaModelerProps {
  readonly session: SchemaModelerSession;
  readonly initialView?: SchemaModelerView;
  readonly labels?: Partial<ProgramKitSchemaModelerLabels>;
  readonly editorMode?: SchemaModelerEditorMode;
  readonly editorAdapter?: JsonEditorAdapter;
  readonly cspNonce?: string;
  readonly classNames?: ProgramKitClassNames<SchemaModelerThemeSlot>;
  readonly className?: string;
  readonly unstyled?: boolean;
  readonly onChange?: (snapshot: SchemaModelerSnapshot) => void;
  readonly onCommit?: (document: SchemaModelerDocument, sequence: number) => void | Promise<void>;
}

const defaultLabels: ProgramKitSchemaModelerLabels = Object.freeze({
  undo: "Undo", redo: "Redo", commit: "Commit schema", applyJson: "Apply JSON Schema",
  design: "Design", json: "JSON Schema", graph: "Graph", palette: "Schema types",
  structure: "Schema structure", canvas: "Schema canvas", inspector: "Properties",
  editor: "JSON Schema source", diagnostics: "Schema diagnostics", remove: "Remove node"
});

interface Appearance { readonly classNames: ProgramKitClassNames<SchemaModelerThemeSlot>; readonly unstyled: boolean; }
const AppearanceContext = createContext<Appearance>({ classNames: {}, unstyled: false });
function useAppearance(): Appearance { return useContext(AppearanceContext); }
function slot(appearance: Appearance, name: SchemaModelerThemeSlot, defaultClass: string, extra?: string): { readonly className: string | undefined; readonly "data-pk-slot": string } {
  return { className: programKitClassName(defaultClass, [appearance.classNames[name], extra].filter(Boolean).join(" ") || undefined, appearance.unstyled), "data-pk-slot": `schema-modeler.${name}` };
}

export function ProgramKitSchemaModeler({ session, initialView = "design", labels: overrides, editorMode = "rich", editorAdapter = codeMirrorJsonEditorAdapter, cspNonce, classNames = {}, className, unstyled = false, onChange, onCommit }: ProgramKitSchemaModelerProps): ReactNode {
  const ids = useId();
  const labels = { ...defaultLabels, ...overrides };
  const [snapshot, setSnapshot] = useState(() => session.snapshot());
  const [view, setView] = useState<SchemaModelerView>(initialView);
  const [source, setSource] = useState(() => serializeCompiledJsonSchema(snapshot.document));
  const [sourceError, setSourceError] = useState("");
  const appearance = { classNames, unstyled };
  const refresh = (next: SchemaModelerSnapshot): void => {
    setSnapshot(next); setSource(serializeCompiledJsonSchema(next.document)); setSourceError(""); onChange?.(next);
  };
  const apply = (operations: readonly SchemaModelerOperation[]): void => {
    try { refresh(session.apply({ commandId: `schema-ui:${snapshot.sequence}:${commandCounter++}`, expectedSequence: snapshot.sequence, operations })); }
    catch (error) { setSourceError(publicError(error)); }
  };
  const select = (id: string): void => refresh(session.select(id));
  const applySource = (): void => {
    try { apply([{ type: "replaceDocument", document: parseCompiledJsonSchema(source, snapshot.document.id, snapshot.document.revision) }]); }
    catch (error) { setSourceError(publicError(error)); }
  };
  const tab = (target: SchemaModelerView, label: string) => <button aria-controls={`${ids}-${target}`} aria-selected={view === target} id={`${ids}-${target}-tab`} onClick={() => setView(target)} role="tab" tabIndex={view === target ? 0 : -1} type="button">{label}</button>;

  return <AppearanceContext.Provider value={appearance}><section {...slot(appearance, "root", "pk-schema-modeler", className)}>
    <div {...slot(appearance, "toolbar", "pk-schema-modeler__toolbar")}>
      <button disabled={!snapshot.canUndo} onClick={() => refresh(session.undo())} type="button">{labels.undo}</button>
      <button disabled={!snapshot.canRedo} onClick={() => refresh(session.redo())} type="button">{labels.redo}</button>
      <button onClick={() => void onCommit?.(snapshot.document, snapshot.sequence)} type="button">{labels.commit}</button>
    </div>
    {sourceError.length > 0 && <p {...slot(appearance, "diagnostics", "pk-schema-modeler__diagnostics")} role="alert">{sourceError}</p>}
    <div aria-label="Schema modeler views" {...slot(appearance, "tabs", "pk-schema-modeler__tabs")} role="tablist">{tab("design", labels.design)}{tab("json", labels.json)}{tab("graph", labels.graph)}</div>
    {view === "design" && <section aria-labelledby={`${ids}-design-tab`} {...slot(appearance, "workspace", "pk-schema-modeler__workspace")} id={`${ids}-design`} role="tabpanel">
      <SchemaPalette document={snapshot.document} labels={labels} selectedId={snapshot.selectedId} onAdd={apply} />
      <SchemaTree document={snapshot.document} label={labels.structure} selectedId={snapshot.selectedId} onSelect={select} />
      <SchemaCanvas document={snapshot.document} label={labels.canvas} selectedId={snapshot.selectedId} onSelect={select} />
      <SchemaInspector document={snapshot.document} label={labels.inspector} selectedId={snapshot.selectedId} removeLabel={labels.remove} onApply={apply} />
    </section>}
    {view === "json" && <section aria-labelledby={`${ids}-json-tab`} id={`${ids}-json`} role="tabpanel">
      <SchemaJsonEditor accessibleLabel={labels.editor} adapter={editorAdapter} {...(cspNonce === undefined ? {} : { cspNonce })} mode={editorMode} onChange={setSource} source={source} />
      <button onClick={applySource} type="button">{labels.applyJson}</button>
    </section>}
    {view === "graph" && <SchemaGraph document={snapshot.document} labelledBy={`${ids}-graph-tab`} panelId={`${ids}-graph`} selectedId={snapshot.selectedId} onSelect={select} />}
  </section></AppearanceContext.Provider>;
}

export function SchemaPalette({ document, selectedId, labels, onAdd }: { readonly document: SchemaModelerDocument; readonly selectedId: string | undefined; readonly labels: ProgramKitSchemaModelerLabels; readonly onAdd: (operations: readonly SchemaModelerOperation[]) => void }): ReactNode {
  const appearance = useAppearance();
  const selected = document.nodes.find(node => node.id === selectedId);
  const parent = selected !== undefined && (selected.valueKind === "object" || selected.valueKind === "array") ? selected : document.nodes.find(node => node.id === selected?.parentId) ?? document.nodes.find(node => node.id === document.rootNodeId);
  const children = parent === undefined ? [] : listSchemaModelerChildren(document, parent.id);
  const arrayFull = parent?.valueKind === "array" && children.length > 0;
  const add = (valueKind: SchemaModelerValueKind): void => {
    if (parent === undefined || arrayFull) return;
    const id = nextNodeId(document, valueKind);
    const propertyName = parent.valueKind === "object" ? nextPropertyName(children, valueKind) : null;
    const node: SchemaModelerNode = { id, parentId: parent.id, propertyName, order: children.length, valueKind, required: false, ...(valueKind === "object" ? { additionalProperties: false } : {}) };
    const operations: SchemaModelerOperation[] = [{ type: "insertNode", parentId: parent.id, index: children.length, node }];
    if (valueKind === "array") operations.push({ type: "insertNode", parentId: id, index: 0, node: { id: `${id}-item`, parentId: id, propertyName: null, order: 0, valueKind: "string", required: false } });
    onAdd(operations);
  };
  return <aside aria-label={labels.palette} {...slot(appearance, "palette", "pk-schema-modeler__palette")}><h2>{labels.palette}</h2>{(["string", "integer", "number", "boolean", "object", "array"] as const).map(kind => <button disabled={parent === undefined || arrayFull} key={kind} onClick={() => add(kind)} type="button">Add {kind}</button>)}</aside>;
}

export function SchemaTree({ document, label, selectedId, onSelect }: { readonly document: SchemaModelerDocument; readonly label: string; readonly selectedId: string | undefined; readonly onSelect: (id: string) => void }): ReactNode {
  const appearance = useAppearance();
  const root = document.nodes.find(node => node.id === document.rootNodeId);
  if (root === undefined) return null;
  const render = (node: SchemaModelerNode): ReactNode => <li key={node.id}><button aria-current={selectedId === node.id} onClick={() => onSelect(node.id)} type="button">{node.propertyName ?? document.title} <small>{node.valueKind}</small></button>{listSchemaModelerChildren(document, node.id).length > 0 && <ul>{listSchemaModelerChildren(document, node.id).map(render)}</ul>}</li>;
  return <nav aria-label={label} {...slot(appearance, "tree", "pk-schema-modeler__tree")}><h2>{label}</h2><ul>{render(root)}</ul></nav>;
}

export function SchemaCanvas({ document, label, selectedId, onSelect }: { readonly document: SchemaModelerDocument; readonly label: string; readonly selectedId: string | undefined; readonly onSelect: (id: string) => void }): ReactNode {
  const appearance = useAppearance();
  const root = document.nodes.find(node => node.id === document.rootNodeId);
  const render = (node: SchemaModelerNode, depth: number): ReactNode => <div {...slot(appearance, "canvasBlock", "pk-schema-modeler__block")} data-depth={depth} key={node.id}><button aria-pressed={selectedId === node.id} onClick={() => onSelect(node.id)} type="button"><strong>{node.propertyName ?? document.title}</strong><small>{node.valueKind}{node.required ? " · required" : ""}</small></button>{listSchemaModelerChildren(document, node.id).map(child => render(child, depth + 1))}</div>;
  return <section aria-label={label} {...slot(appearance, "canvas", "pk-schema-modeler__canvas")}><h2>{label}</h2>{root === undefined ? null : render(root, 0)}</section>;
}

export function SchemaInspector({ document, selectedId, label, removeLabel, onApply }: { readonly document: SchemaModelerDocument; readonly selectedId: string | undefined; readonly label: string; readonly removeLabel: string; readonly onApply: (operations: readonly SchemaModelerOperation[]) => void }): ReactNode {
  const appearance = useAppearance();
  const node = document.nodes.find(candidate => candidate.id === (selectedId ?? document.rootNodeId));
  const [propertyName, setPropertyName] = useState(node?.propertyName ?? "");
  const [title, setTitle] = useState(node?.title ?? "");
  useEffect(() => { setPropertyName(node?.propertyName ?? ""); setTitle(node?.title ?? ""); }, [node?.id, node?.propertyName, node?.title]);
  if (node === undefined) return null;
  const update = (changes: Partial<SchemaModelerNode>): void => onApply([{ type: "updateNode", node: { ...node, ...changes } }]);
  return <aside aria-label={label} {...slot(appearance, "inspector", "pk-schema-modeler__inspector")}><h2>{label}</h2>
    <dl><dt>ID</dt><dd>{node.id}</dd><dt>Type</dt><dd>{node.valueKind}</dd></dl>
    {node.parentId !== null && node.propertyName !== null && <label>Property name<input onBlur={() => { if (propertyName !== node.propertyName) update({ propertyName }); }} onChange={event => setPropertyName(event.currentTarget.value)} value={propertyName} /></label>}
    <label>Title<input onBlur={() => { if (title !== (node.title ?? "")) update({ title: title.length === 0 ? null : title }); }} onChange={event => setTitle(event.currentTarget.value)} value={title} /></label>
    {node.propertyName !== null && <label><input checked={node.required} onChange={event => update({ required: event.currentTarget.checked })} type="checkbox" /> Required</label>}
    {node.valueKind === "object" && <label><input checked={node.additionalProperties === true} onChange={event => update({ additionalProperties: event.currentTarget.checked })} type="checkbox" /> Allow undeclared properties</label>}
    {node.id !== document.rootNodeId && <button onClick={() => onApply([{ type: "removeNode", nodeId: node.id }])} type="button">{removeLabel}</button>}
  </aside>;
}

export function SchemaJsonEditor({ source, accessibleLabel, adapter = codeMirrorJsonEditorAdapter, cspNonce, mode, onChange }: { readonly source: string; readonly accessibleLabel: string; readonly adapter?: JsonEditorAdapter; readonly cspNonce?: string; readonly mode: SchemaModelerEditorMode; readonly onChange: (source: string) => void }): ReactNode {
  const appearance = useAppearance();
  const parent = useRef<HTMLDivElement>(null);
  const handle = useRef<JsonEditorHandle | null>(null);
  useEffect(() => {
    if (mode === "strictCsp" || parent.current === null) return;
    handle.current = adapter.mount({ parent: parent.current, document: source, accessibleLabel, onChange, diagnostics: schemaSourceDiagnostics, ...(cspNonce === undefined ? {} : { cspNonce }) });
    return () => { handle.current?.destroy(); handle.current = null; };
  }, [accessibleLabel, adapter, cspNonce, mode, onChange]);
  useEffect(() => handle.current?.setDocument(source), [source]);
  if (mode === "strictCsp") return <textarea aria-label={accessibleLabel} {...slot(appearance, "editor", "pk-schema-modeler__editor pk-schema-modeler__editor--strict")} onChange={event => onChange(event.currentTarget.value)} spellCheck={false} value={source} />;
  return <div {...slot(appearance, "editor", "pk-schema-modeler__editor")} ref={parent} />;
}

export function SchemaGraph({ document, labelledBy, panelId, selectedId, onSelect }: { readonly document: SchemaModelerDocument; readonly labelledBy?: string; readonly panelId?: string; readonly selectedId: string | undefined; readonly onSelect: (id: string) => void }): ReactNode {
  const appearance = useAppearance();
  const graph = projectSchemaModelerGraph(document);
  return <section aria-labelledby={labelledBy} {...slot(appearance, "graph", "pk-schema-modeler__graph")} id={panelId} role="tabpanel"><div className="pk-schema-modeler__graph-nodes">{graph.nodes.map(node => <button aria-pressed={selectedId === node.id} {...slot(appearance, "graphNode", "pk-schema-modeler__graph-node")} key={node.id} onClick={() => onSelect(node.id)} type="button"><strong>{node.label}</strong><small>{node.valueKind}</small></button>)}</div><table><thead><tr><th>From</th><th>Relationship</th><th>To</th></tr></thead><tbody>{graph.edges.map(edge => <tr key={`${edge.from}:${edge.to}`}><td>{edge.from}</td><td>{edge.label ?? edge.kind}</td><td>{edge.to}</td></tr>)}</tbody></table></section>;
}

function schemaSourceDiagnostics(source: string) { try { parseCompiledJsonSchema(source); return []; } catch (error) { return [{ from: 0, to: source.length, severity: "error" as const, message: publicError(error) }]; } }
function publicError(error: unknown): string { return error instanceof SchemaModelerValidationError || error instanceof SyntaxError || error instanceof Error ? error.message : "The schema operation could not be completed."; }
function nextNodeId(document: SchemaModelerDocument, kind: string): string { let index = 1; while (document.nodes.some(node => node.id === `${kind}-${index}` || node.id === `${kind}-${index}-item`)) index += 1; return `${kind}-${index}`; }
function nextPropertyName(children: readonly SchemaModelerNode[], kind: string): string { let index = 1; while (children.some(node => node.propertyName === `${kind}${index}`)) index += 1; return `${kind}${index}`; }
let commandCounter = 1;
