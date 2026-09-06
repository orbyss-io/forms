import { ChangeDetectionStrategy, Component, ElementRef, EventEmitter, Input, Output, ViewChild, type AfterViewChecked, type OnDestroy, type OnInit } from "@angular/core";
import { codeMirrorJsonEditorAdapter } from "@orbyss/program-kit-forms-codemirror";
import type { JsonEditorAdapter, JsonEditorHandle } from "@orbyss/program-kit-forms-editor-contracts";
import {
  SchemaModelerSession,
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

export type SchemaModelerAngularView = "design" | "json" | "graph";
export type SchemaModelerAngularEditorMode = "rich" | "strictCsp";
export type SchemaModelerAngularThemeSlot = "root" | "toolbar" | "diagnostics" | "tabs" | "workspace" | "palette" | "tree" | "canvas" | "canvasBlock" | "inspector" | "editor" | "graph" | "graphNode";
export interface ProgramKitSchemaModelerAngularLabels { readonly undo: string; readonly redo: string; readonly commit: string; readonly applyJson: string; readonly design: string; readonly json: string; readonly graph: string; readonly palette: string; readonly structure: string; readonly canvas: string; readonly inspector: string; readonly editor: string; readonly remove: string; }
const defaults: ProgramKitSchemaModelerAngularLabels = Object.freeze({ undo: "Undo", redo: "Redo", commit: "Commit schema", applyJson: "Apply JSON Schema", design: "Design", json: "JSON Schema", graph: "Graph", palette: "Schema types", structure: "Schema structure", canvas: "Schema canvas", inspector: "Properties", editor: "JSON Schema source", remove: "Remove node" });
const kinds: readonly SchemaModelerValueKind[] = ["string", "integer", "number", "boolean", "object", "array"];

@Component({
  selector: "program-kit-schema-modeler",
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section [class]="slotClass('root', 'pk-schema-modeler', className)" data-pk-slot="schema-modeler.root" [attr.data-pk-unstyled]="unstyled || null">
      <div [class]="slotClass('toolbar', 'pk-schema-modeler__toolbar')" data-pk-slot="schema-modeler.toolbar" role="toolbar" aria-label="Schema modeler actions">
        <button type="button" [disabled]="!snapshot.canUndo" (click)="refresh(session.undo())">{{ text.undo }}</button>
        <button type="button" [disabled]="!snapshot.canRedo" (click)="refresh(session.redo())">{{ text.redo }}</button>
        <button type="button" (click)="commit.emit({ document: snapshot.document, sequence: snapshot.sequence })">{{ text.commit }}</button>
      </div>
      @if (error) { <p [class]="slotClass('diagnostics', 'pk-schema-modeler__diagnostics')" data-pk-slot="schema-modeler.diagnostics" role="alert">{{ error }}</p> }
      <div [class]="slotClass('tabs', 'pk-schema-modeler__tabs')" data-pk-slot="schema-modeler.tabs" role="tablist" aria-label="Schema modeler views">
        @for (candidate of views; track candidate) { <button type="button" role="tab" [attr.aria-selected]="view === candidate" (click)="setView(candidate)">{{ viewLabel(candidate) }}</button> }
      </div>
      @if (view === 'design') {
        <section [class]="slotClass('workspace', 'pk-schema-modeler__workspace')" data-pk-slot="schema-modeler.workspace">
          <aside [class]="slotClass('palette', 'pk-schema-modeler__palette')" data-pk-slot="schema-modeler.palette" [attr.aria-label]="text.palette"><h2>{{ text.palette }}</h2>
            @for (kind of kinds; track kind) { <button type="button" [disabled]="!canAdd(kind)" (click)="add(kind)">Add {{ kind }}</button> }
          </aside>
          <nav [class]="slotClass('tree', 'pk-schema-modeler__tree')" data-pk-slot="schema-modeler.tree" [attr.aria-label]="text.structure"><h2>{{ text.structure }}</h2><ul>
            @for (node of orderedNodes(); track node.id) { <li><button type="button" [attr.aria-current]="snapshot.selectedId === node.id" (click)="select(node.id)">{{ node.propertyName || snapshot.document.title }} <small>{{ node.valueKind }}</small></button></li> }
          </ul></nav>
          <section [class]="slotClass('canvas', 'pk-schema-modeler__canvas')" data-pk-slot="schema-modeler.canvas" [attr.aria-label]="text.canvas"><h2>{{ text.canvas }}</h2>
            @for (node of orderedNodes(); track node.id) { <div [class]="slotClass('canvasBlock', 'pk-schema-modeler__block')" data-pk-slot="schema-modeler.canvasBlock"><button type="button" [attr.aria-pressed]="snapshot.selectedId === node.id" (click)="select(node.id)"><strong>{{ node.propertyName || snapshot.document.title }}</strong><small>{{ node.valueKind }}{{ node.required ? ' · required' : '' }}</small></button></div> }
          </section>
          <aside [class]="slotClass('inspector', 'pk-schema-modeler__inspector')" data-pk-slot="schema-modeler.inspector" [attr.aria-label]="text.inspector"><h2>{{ text.inspector }}</h2>
            @if (selected(); as node) { <dl><dt>ID</dt><dd>{{ node.id }}</dd><dt>Type</dt><dd>{{ node.valueKind }}</dd></dl>
              @if (node.propertyName !== null) { <label>Property name<input [value]="node.propertyName" (change)="updateProperty(node, value($event))"></label> }
              <label>Title<input [value]="node.title || ''" (change)="updateTitle(node, value($event))"></label>
              @if (node.propertyName !== null) { <label><input type="checkbox" [checked]="node.required" (change)="updateRequired(node, checked($event))"> Required</label> }
              @if (node.id !== snapshot.document.rootNodeId) { <button type="button" (click)="remove(node.id)">{{ text.remove }}</button> }
            }
          </aside>
        </section>
      }
      @if (view === 'json') { <section role="tabpanel"><div #editorHost [hidden]="editorMode === 'strictCsp'" [class]="slotClass('editor', 'pk-schema-modeler__editor')" data-pk-slot="schema-modeler.editor"></div>
        @if (editorMode === 'strictCsp') { <textarea [class]="slotClass('editor', 'pk-schema-modeler__editor pk-schema-modeler__editor--strict')" data-pk-slot="schema-modeler.editor" [attr.aria-label]="text.editor" spellcheck="false" [value]="source" (input)="source = value($event)"></textarea> }
        <button type="button" (click)="applySource()">{{ text.applyJson }}</button></section> }
      @if (view === 'graph') { <section [class]="slotClass('graph', 'pk-schema-modeler__graph')" data-pk-slot="schema-modeler.graph" role="tabpanel"><div class="pk-schema-modeler__graph-nodes">
        @for (node of graph().nodes; track node.id) { <button type="button" [class]="slotClass('graphNode', 'pk-schema-modeler__graph-node')" data-pk-slot="schema-modeler.graphNode" [attr.aria-pressed]="snapshot.selectedId === node.id" (click)="select(node.id)"><strong>{{ node.label }}</strong><small>{{ node.valueKind }}</small></button> }
        </div><table><thead><tr><th>From</th><th>Relationship</th><th>To</th></tr></thead><tbody>@for (edge of graph().edges; track edge.from + edge.to) { <tr><td>{{ edge.from }}</td><td>{{ edge.label || edge.kind }}</td><td>{{ edge.to }}</td></tr> }</tbody></table></section> }
    </section>
  `
})
export class ProgramKitSchemaModelerAngularComponent implements OnInit, AfterViewChecked, OnDestroy {
  @Input({ required: true }) session!: SchemaModelerSession;
  @Input() initialView: SchemaModelerAngularView = "design";
  @Input() labels: Partial<ProgramKitSchemaModelerAngularLabels> = {};
  @Input() editorMode: SchemaModelerAngularEditorMode = "rich";
  @Input() editorAdapter: JsonEditorAdapter = codeMirrorJsonEditorAdapter;
  @Input() cspNonce?: string;
  @Input() classNames: ProgramKitClassNames<SchemaModelerAngularThemeSlot> = {};
  @Input() className?: string;
  @Input() unstyled = false;
  @Output() readonly change = new EventEmitter<SchemaModelerSnapshot>();
  @Output() readonly commit = new EventEmitter<{ readonly document: SchemaModelerDocument; readonly sequence: number }>();
  @ViewChild("editorHost") editorHost?: ElementRef<HTMLElement>;
  readonly views: readonly SchemaModelerAngularView[] = ["design", "json", "graph"];
  readonly kinds = kinds;
  snapshot!: SchemaModelerSnapshot;
  view: SchemaModelerAngularView = "design";
  source = "";
  error = "";
  private editor: JsonEditorHandle | undefined;
  private editorElement: HTMLElement | undefined;
  private command = 1;
  get text(): ProgramKitSchemaModelerAngularLabels { return { ...defaults, ...this.labels }; }
  ngOnInit(): void { this.view = this.initialView; this.snapshot = this.session.snapshot(); this.source = serializeCompiledJsonSchema(this.snapshot.document); }
  ngAfterViewChecked(): void { const host = this.view === "json" && this.editorMode === "rich" ? this.editorHost?.nativeElement : undefined; if (host === this.editorElement) return; this.destroyEditor(); if (host !== undefined) { this.editorElement = host; this.editor = this.editorAdapter.mount({ parent: host, document: this.source, accessibleLabel: this.text.editor, onChange: value => { this.source = value; }, diagnostics: source => { try { parseCompiledJsonSchema(source); return []; } catch (reason) { return [{ from: 0, to: source.length, severity: "error", message: publicError(reason) }]; } }, ...(this.cspNonce === undefined ? {} : { cspNonce: this.cspNonce }) }); } }
  ngOnDestroy(): void { this.destroyEditor(); }
  slotClass(name: SchemaModelerAngularThemeSlot, base: string, extra?: string): string | undefined { return programKitClassName(base, [this.classNames[name], extra].filter(Boolean).join(" ") || undefined, this.unstyled); }
  viewLabel(view: SchemaModelerAngularView): string { return this.text[view]; }
  setView(view: SchemaModelerAngularView): void { this.view = view; if (view !== "json") this.destroyEditor(); }
  refresh(next: SchemaModelerSnapshot): void { this.snapshot = next; this.source = serializeCompiledJsonSchema(next.document); this.editor?.setDocument(this.source); this.error = ""; this.change.emit(next); }
  apply(operations: readonly SchemaModelerOperation[]): boolean { try { this.refresh(this.session.apply({ commandId: `schema-angular:${this.snapshot.sequence}:${this.command++}`, expectedSequence: this.snapshot.sequence, operations })); return true; } catch (reason) { this.error = publicError(reason); return false; } }
  applySource(): void { try { this.apply([{ type: "replaceDocument", document: parseCompiledJsonSchema(this.source, this.snapshot.document.id, this.snapshot.document.revision) }]); } catch (reason) { this.error = publicError(reason); } }
  select(id: string): void { this.refresh(this.session.select(id)); }
  selected(): SchemaModelerNode | undefined { return this.snapshot.document.nodes.find(node => node.id === this.snapshot.selectedId) ?? this.snapshot.document.nodes.find(node => node.id === this.snapshot.document.rootNodeId); }
  orderedNodes(): readonly SchemaModelerNode[] { const result: SchemaModelerNode[] = []; const visit = (id: string) => { const node = this.snapshot.document.nodes.find(value => value.id === id); if (node === undefined) return; result.push(node); listSchemaModelerChildren(this.snapshot.document, id).forEach(child => visit(child.id)); }; visit(this.snapshot.document.rootNodeId); return result; }
  graph(): ReturnType<typeof projectSchemaModelerGraph> { return projectSchemaModelerGraph(this.snapshot.document); }
  canAdd(_kind: SchemaModelerValueKind): boolean { const selected = this.selected(); const parent = selected !== undefined && (selected.valueKind === "object" || selected.valueKind === "array") ? selected : this.snapshot.document.nodes.find(node => node.id === selected?.parentId); return parent !== undefined && !(parent.valueKind === "array" && listSchemaModelerChildren(this.snapshot.document, parent.id).length > 0); }
  add(kind: SchemaModelerValueKind): void { const selected = this.selected(); const parent = selected !== undefined && (selected.valueKind === "object" || selected.valueKind === "array") ? selected : this.snapshot.document.nodes.find(node => node.id === selected?.parentId); if (parent === undefined || !this.canAdd(kind)) return; const children = listSchemaModelerChildren(this.snapshot.document, parent.id); const id = nextId(this.snapshot.document, kind); const node: SchemaModelerNode = { id, parentId: parent.id, propertyName: parent.valueKind === "object" ? nextProperty(children, kind) : null, order: children.length, valueKind: kind, required: false, ...(kind === "object" ? { additionalProperties: false } : {}) }; const operations: SchemaModelerOperation[] = [{ type: "insertNode", parentId: parent.id, index: children.length, node }]; if (kind === "array") operations.push({ type: "insertNode", parentId: id, index: 0, node: { id: `${id}-item`, parentId: id, propertyName: null, order: 0, valueKind: "string", required: false } }); if (this.apply(operations)) this.select(id); }
  remove(id: string): void { this.apply([{ type: "removeNode", nodeId: id }]); }
  updateProperty(node: SchemaModelerNode, propertyName: string): void { this.apply([{ type: "updateNode", node: { ...node, propertyName } }]); }
  updateTitle(node: SchemaModelerNode, title: string): void { this.apply([{ type: "updateNode", node: { ...node, title: title.length === 0 ? null : title } }]); }
  updateRequired(node: SchemaModelerNode, required: boolean): void { this.apply([{ type: "updateNode", node: { ...node, required } }]); }
  value(event: Event): string { return (event.currentTarget as HTMLInputElement | HTMLTextAreaElement).value; }
  checked(event: Event): boolean { return (event.currentTarget as HTMLInputElement).checked; }
  private destroyEditor(): void { this.editor?.destroy(); this.editor = undefined; this.editorElement = undefined; }
}

function publicError(reason: unknown): string { return reason instanceof Error ? reason.message : "The schema operation could not be completed."; }
function nextId(document: SchemaModelerDocument, kind: string): string { let value = 1; while (document.nodes.some(node => node.id === `${kind}-${value}` || node.id === `${kind}-${value}-item`)) value += 1; return `${kind}-${value}`; }
function nextProperty(children: readonly SchemaModelerNode[], kind: string): string { let value = 1; while (children.some(node => node.propertyName === `${kind}${value}`)) value += 1; return `${kind}${value}`; }
