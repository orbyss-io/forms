import { createContext, useContext, useEffect, useId, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import {
  projectLocalizationRows,
  validateLocalizationDocument,
  type LocalizationActor,
  type LocalizationArgument,
  type LocalizationArgumentType,
  type LocalizationFilters,
  type LocalizationImportPreview,
  type LocalizationImportSubmission,
  type LocalizationInterchangeFormat,
  type LocalizationManagementSession,
  type LocalizationMergePolicy,
  type LocalizationMessage,
  type LocalizationRow,
  type LocalizationScope,
  type LocalizationScopeKind,
  type LocalizationSnapshot,
  type LocalizationValueState
} from "@orbyss/program-kit-localization-management";
import {
  programKitClassName,
  type ProgramKitClassNames
} from "@orbyss/program-kit-ui-theme";

export interface LocalizationFormOption { readonly id: string; readonly name: string; }
export interface LocalizationCapabilities { readonly edit?: boolean; readonly add?: boolean; readonly import?: boolean; readonly export?: boolean; readonly review?: boolean; readonly approve?: boolean; readonly publish?: boolean; }
export type LocalizationLifecycleAction = "submitForReview" | "approve" | "publish";
export type LocalizationManagementThemeSlot =
  | "root" | "toolbar" | "filters" | "diagnostics" | "table" | "paging"
  | "dialog" | "dialogFields" | "dialogActions" | "row" | "importReview";
export interface LocalizationManagementLabels {
  readonly undo: string; readonly redo: string; readonly add: string; readonly import: string; readonly export: string;
  readonly submitForReview: string; readonly approve: string; readonly publish: string; readonly search: string;
  readonly locale: string; readonly scope: string; readonly form: string; readonly status: string; readonly missingOnly: string;
  readonly translations: string; readonly key: string; readonly source: string; readonly translation: string; readonly previous: string;
  readonly next: string; readonly rows: string; readonly diagnostics: string; readonly importPreview: string; readonly applyImport: string;
  readonly addTitle: string; readonly create: string; readonly cancel: string; readonly resourceId: string; readonly parentResourceId: string;
  readonly description: string; readonly context: string; readonly arguments: string; readonly argumentName: string; readonly argumentType: string;
  readonly required: string; readonly addArgument: string; readonly removeArgument: string;
  readonly importTitle: string; readonly file: string; readonly format: string; readonly mergePolicy: string; readonly targetLocale: string;
  readonly mappings: string; readonly mappingRole: string; readonly mappingColumn: string; readonly addMapping: string; readonly removeMapping: string;
  readonly previewImport: string; readonly importFromFile: string;
}
export interface ProgramKitLocalizationManagementProps {
  readonly session: LocalizationManagementSession;
  readonly actor: LocalizationActor;
  readonly labels?: Partial<LocalizationManagementLabels>;
  readonly capabilities?: LocalizationCapabilities;
  readonly forms?: readonly LocalizationFormOption[];
  readonly pageSize?: number;
  readonly maximumImportBytes?: number;
  readonly importPreview?: LocalizationImportPreview;
  /** Additional classes for stable visual slots; behavior never depends on these values. */
  readonly classNames?: ProgramKitClassNames<LocalizationManagementThemeSlot>;
  /** Additional class for the root management surface. */
  readonly className?: string;
  /** Omits all Program Kit baseline classes while preserving semantic data-pk-slot hooks. */
  readonly unstyled?: boolean;
  readonly onChange?: (snapshot: LocalizationSnapshot) => void;
  readonly onAddRequested?: () => void;
  readonly onMessageAdded?: (message: LocalizationMessage, snapshot: LocalizationSnapshot) => void;
  readonly onImportRequested?: () => void;
  readonly onPreviewImport?: (submission: LocalizationImportSubmission) => Promise<LocalizationImportPreview>;
  readonly onExportRequested?: (filters: LocalizationFilters) => void;
  readonly onApplyImport?: (previewId: string) => void | Promise<void>;
  readonly onLifecycleAction?: (action: LocalizationLifecycleAction, snapshot: LocalizationSnapshot) => void | Promise<void>;
}

interface LocalizationAppearance {
  readonly classNames: ProgramKitClassNames<LocalizationManagementThemeSlot>;
  readonly unstyled: boolean;
}

const LocalizationAppearanceContext = createContext<LocalizationAppearance>({ classNames: {}, unstyled: false });

function localizationSlot(
  appearance: LocalizationAppearance,
  slot: LocalizationManagementThemeSlot,
  defaultClassName: string,
  extraClassName?: string
): { readonly className: string | undefined; readonly "data-pk-slot": string } {
  return {
    className: programKitClassName(defaultClassName, [appearance.classNames[slot], extraClassName].filter(Boolean).join(" ") || undefined, appearance.unstyled),
    "data-pk-slot": `localization-management.${slot}`
  };
}

function useLocalizationAppearance(): LocalizationAppearance {
  return useContext(LocalizationAppearanceContext);
}

const defaultLabels: LocalizationManagementLabels = Object.freeze({
  undo: "Undo", redo: "Redo", add: "Add message", import: "Import", export: "Export",
  submitForReview: "Submit for review", approve: "Approve", publish: "Publish", search: "Search",
  locale: "Locale", scope: "Scope", form: "Form", status: "Status", missingOnly: "Missing only",
  translations: "Translations", key: "Key", source: "Source", translation: "Translation", previous: "Previous rows",
  next: "Next rows", rows: "rows", diagnostics: "Catalog diagnostics", importPreview: "Import preview", applyImport: "Apply import",
  addTitle: "Add localization message", create: "Create message", cancel: "Cancel", resourceId: "Resource ID", parentResourceId: "Parent resource ID",
  description: "Description", context: "Context", arguments: "Arguments", argumentName: "Argument name", argumentType: "Argument type",
  required: "Required", addArgument: "Add argument", removeArgument: "Remove argument", importTitle: "Preview localization import",
  file: "Import file", format: "Format", mergePolicy: "Merge policy", targetLocale: "Target locale", mappings: "Column mappings",
  mappingRole: "Semantic role", mappingColumn: "Source column", addMapping: "Add mapping", removeMapping: "Remove mapping",
  previewImport: "Preview import", importFromFile: "Read scope from file"
});
const scopeKinds: readonly LocalizationScopeKind[] = ["application", "feature", "form", "formValidation", "custom"];
const valueStates: readonly LocalizationValueState[] = ["draft", "machineSuggested", "reviewed", "approved"];
const argumentTypes: readonly LocalizationArgumentType[] = ["string", "number", "integer", "date", "dateTime", "time", "select"];
const formScopeKinds = new Set<LocalizationScopeKind>(["form", "formValidation"]);
const interchangeFormats: readonly LocalizationInterchangeFormat[] = ["csv", "xlsx", "json", "xliff21", "po"];
const mergePolicies: readonly LocalizationMergePolicy[] = ["addOnly", "preserveExisting", "replaceImported", "replaceScope"];

export function ProgramKitLocalizationManagement({ session, actor, labels: overrides, capabilities = {}, forms = [], pageSize = 50, maximumImportBytes = 8 * 1024 * 1024, importPreview, classNames = {}, className, unstyled = false, onChange, onAddRequested, onMessageAdded, onImportRequested, onPreviewImport, onExportRequested, onApplyImport, onLifecycleAction }: ProgramKitLocalizationManagementProps): ReactNode {
  if (!Number.isSafeInteger(pageSize) || pageSize < 1 || pageSize > 200) throw new Error("Localization page size must be between 1 and 200.");
  if (!Number.isSafeInteger(maximumImportBytes) || maximumImportBytes < 1) throw new Error("Localization import byte limit must be a positive safe integer.");
  const labels = { ...defaultLabels, ...overrides };
  const [snapshot, setSnapshot] = useState(() => session.snapshot());
  const [filters, setFilters] = useState<LocalizationFilters>({});
  const [first, setFirst] = useState(0);
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [reviewedImport, setReviewedImport] = useState<LocalizationImportPreview | undefined>(importPreview);
  const commandNumber = useRef(0);
  const rows = useMemo(() => projectLocalizationRows(snapshot.document, filters, first, pageSize), [snapshot.document, filters, first, pageSize]);
  const diagnostics = useMemo(() => validateLocalizationDocument(snapshot.document), [snapshot.document]);
  const errors = diagnostics.filter(item => item.severity === "error");
  const refresh = (next: LocalizationSnapshot) => { setSnapshot(next); onChange?.(next); };
  const setFilter = <K extends keyof LocalizationFilters>(key: K, value: LocalizationFilters[K]) => { setFilters(current => ({ ...current, [key]: value === "" ? undefined : value })); setFirst(0); };
  const setValue = (row: LocalizationRow, pattern: string, state: LocalizationValueState) => refresh(session.apply({
    commandId: `localization-${snapshot.sequence}-${++commandNumber.current}`,
    expectedSequence: snapshot.sequence,
    actor,
    requestedAt: new Date().toISOString(),
    operations: [{ type: "setValue", key: row.key, scope: row.scope, value: { languageTag: row.languageTag, pattern, state, provenance: "human", updatedAt: new Date().toISOString(), updatedBy: actor } }]
  }));
  const addMessage = (message: LocalizationMessage) => {
    const next = session.apply({ commandId: `localization-${snapshot.sequence}-${++commandNumber.current}`, expectedSequence: snapshot.sequence, actor, requestedAt: new Date().toISOString(), operations: [{ type: "addMessage", message }] });
    refresh(next); onMessageAdded?.(message, next);
  };
  const transition = (action: LocalizationLifecycleAction) => { if (onLifecycleAction !== undefined) void onLifecycleAction(action, snapshot); };
  useEffect(() => setReviewedImport(importPreview), [importPreview]);
  const appearance = useMemo<LocalizationAppearance>(() => ({ classNames, unstyled }), [classNames, unstyled]);
  return <LocalizationAppearanceContext.Provider value={appearance}><section {...localizationSlot(appearance, "root", "pk-localization", className)} data-pk-unstyled={unstyled || undefined}>
    <div aria-label="Localization actions" {...localizationSlot(appearance, "toolbar", "pk-localization__toolbar")} role="toolbar">
      <button disabled={!snapshot.canUndo} onClick={() => refresh(session.undo())} type="button">{labels.undo}</button>
      <button disabled={!snapshot.canRedo} onClick={() => refresh(session.redo())} type="button">{labels.redo}</button>
      {(capabilities.add !== undefined || onAddRequested !== undefined) && <button disabled={capabilities.add !== true} onClick={() => { onAddRequested?.(); setAddOpen(true); }} type="button">{labels.add}</button>}
      {(onImportRequested !== undefined || onPreviewImport !== undefined) && <button disabled={capabilities.import !== true} onClick={() => { onImportRequested?.(); if (onPreviewImport !== undefined) setImportOpen(true); }} type="button">{labels.import}</button>}
      {onExportRequested !== undefined && <button disabled={capabilities.export !== true} onClick={() => onExportRequested(filters)} type="button">{labels.export}</button>}
      {onLifecycleAction !== undefined && <><button disabled={capabilities.review !== true || snapshot.document.state !== "validated" || errors.length > 0} onClick={() => transition("submitForReview")} type="button">{labels.submitForReview}</button><button disabled={capabilities.approve !== true || snapshot.document.state !== "inReview" || errors.length > 0} onClick={() => transition("approve")} type="button">{labels.approve}</button><button disabled={capabilities.publish !== true || snapshot.document.state !== "approved" || diagnostics.some(item => item.severity !== "information")} onClick={() => transition("publish")} type="button">{labels.publish}</button></>}
    </div>
    <div aria-label="Translation filters" {...localizationSlot(appearance, "filters", "pk-localization__filters")} role="search">
      <label>{labels.search}<input onChange={event => setFilter("text", event.currentTarget.value)} type="search" value={filters.text ?? ""} /></label>
      <label>{labels.locale}<select onChange={event => setFilter("locale", event.currentTarget.value)} value={filters.locale ?? ""}><option value="">All</option>{snapshot.document.locales.filter(locale => locale.languageTag.toLowerCase() !== snapshot.document.sourceLocale.toLowerCase()).map(locale => <option key={locale.languageTag} value={locale.languageTag}>{locale.languageTag}</option>)}</select></label>
      <label>{labels.scope}<select onChange={event => setFilter("scopeKind", event.currentTarget.value.length === 0 ? undefined : event.currentTarget.value as LocalizationScopeKind)} value={filters.scopeKind ?? ""}><option value="">All</option>{scopeKinds.map(kind => <option key={kind} value={kind}>{kind}</option>)}</select></label>
      {forms.length > 0 && <label>{labels.form}<select onChange={event => setFilter("formId", event.currentTarget.value)} value={filters.formId ?? ""}><option value="">All</option>{forms.map(form => <option key={form.id} value={form.id}>{form.name}</option>)}</select></label>}
      <label>{labels.status}<select onChange={event => setFilter("state", event.currentTarget.value.length === 0 ? undefined : event.currentTarget.value as LocalizationValueState | "missing")} value={filters.state ?? ""}><option value="">All</option><option value="missing">Missing</option>{valueStates.map(state => <option key={state} value={state}>{state}</option>)}</select></label>
      <label><input checked={filters.missingOnly === true} onChange={event => setFilter("missingOnly", event.currentTarget.checked)} type="checkbox" /> {labels.missingOnly}</label>
    </div>
    {diagnostics.length > 0 && <div aria-label={labels.diagnostics} {...localizationSlot(appearance, "diagnostics", "pk-localization__diagnostics")}><strong>{labels.diagnostics}</strong><ul>{diagnostics.map((item, index) => <li data-severity={item.severity} key={`${item.code}-${item.key ?? ""}-${item.languageTag ?? ""}-${index}`}>{item.message}</li>)}</ul></div>}
    <div {...localizationSlot(appearance, "table", "pk-localization__table-wrap")}><table><caption>{labels.translations}: {rows.total} {labels.rows}</caption><thead><tr><th>{labels.key}</th><th>{labels.scope}</th><th>{labels.source}</th><th>{labels.locale}</th><th>{labels.translation}</th><th>{labels.status}</th></tr></thead><tbody>{rows.rows.map(row => <LocalizationRowEditor canEdit={capabilities.edit === true} key={row.id} labels={labels} onCommit={setValue} row={row} />)}</tbody></table>{rows.total === 0 && <p className="pk-localization__empty">No translations match the filters.</p>}</div>
    <div {...localizationSlot(appearance, "paging", "pk-localization__paging")}><button disabled={!rows.hasPrevious} onClick={() => setFirst(Math.max(0, rows.first - pageSize))} type="button">{labels.previous}</button><span>{rows.total === 0 ? 0 : rows.first + 1}–{Math.min(rows.first + rows.rows.length, rows.total)} / {rows.total}</span><button disabled={!rows.hasNext} onClick={() => setFirst(rows.first + pageSize)} type="button">{labels.next}</button></div>
    {reviewedImport !== undefined && <LocalizationImportReview labels={labels} onApply={onApplyImport} preview={reviewedImport} />}
    {addOpen && <LocalizationAddMessageDialog forms={forms} labels={labels} onCancel={() => setAddOpen(false)} onCreate={message => { addMessage(message); setAddOpen(false); }} />}
    {importOpen && onPreviewImport !== undefined && <LocalizationImportDialog forms={forms} labels={labels} maximumBytes={maximumImportBytes} onCancel={() => setImportOpen(false)} onPreview={async submission => { const preview = await onPreviewImport(submission); setReviewedImport(preview); setImportOpen(false); }} />}
  </section></LocalizationAppearanceContext.Provider>;
}

function LocalizationAddMessageDialog({ labels, forms, onCancel, onCreate }: { readonly labels: LocalizationManagementLabels; readonly forms: readonly LocalizationFormOption[]; readonly onCancel: () => void; readonly onCreate: (message: LocalizationMessage) => void }): ReactNode {
  const appearance = useLocalizationAppearance();
  const titleId = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const keyInput = useRef<HTMLInputElement>(null);
  const [key, setKey] = useState("");
  const [scopeKind, setScopeKind] = useState<LocalizationScopeKind>("application");
  const [resourceId, setResourceId] = useState("");
  const [parentResourceId, setParentResourceId] = useState("");
  const [sourcePattern, setSourcePattern] = useState("");
  const [description, setDescription] = useState("");
  const [context, setContext] = useState("");
  const [argumentsList, setArgumentsList] = useState<readonly LocalizationArgument[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    const element = dialog.current;
    if (element !== null && !element.open) element.showModal();
    keyInput.current?.focus();
    return () => { if (element?.open === true) element.close(); };
  }, []);
  const updateArgument = (index: number, update: Partial<LocalizationArgument>) => setArgumentsList(current => current.map((argument, position) => position === index ? { ...argument, ...update } : argument));
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    const scope: LocalizationScope = scopeKind === "application" ? { kind: scopeKind } : { kind: scopeKind, resourceId, ...(parentResourceId.trim().length === 0 ? {} : { parentResourceId }) };
    const message: LocalizationMessage = { key, scope, sourcePattern, arguments: argumentsList, values: [], ...(description.trim().length === 0 ? {} : { description }), ...(context.trim().length === 0 ? {} : { context }) };
    try { onCreate(message); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "The localization message could not be created."); }
  };
  return <dialog aria-labelledby={titleId} {...localizationSlot(appearance, "dialog", "pk-localization__dialog")} onCancel={event => { event.preventDefault(); onCancel(); }} ref={dialog}>
    <form method="dialog" onSubmit={submit}>
      <h2 id={titleId}>{labels.addTitle}</h2>
      {error.length > 0 && <p className="pk-localization__dialog-error" role="alert">{error}</p>}
      <div {...localizationSlot(appearance, "dialogFields", "pk-localization__dialog-fields")}>
        <label>{labels.key}<input autoComplete="off" onChange={event => setKey(event.currentTarget.value)} ref={keyInput} required value={key} /></label>
        <label>{labels.scope}<select onChange={event => { const next = event.currentTarget.value as LocalizationScopeKind; setScopeKind(next); if (next === "application") { setResourceId(""); setParentResourceId(""); } }} value={scopeKind}>{scopeKinds.map(kind => <option key={kind} value={kind}>{kind}</option>)}</select></label>
        {scopeKind !== "application" && (formScopeKinds.has(scopeKind) && forms.length > 0
          ? <label>{labels.resourceId}<select onChange={event => setResourceId(event.currentTarget.value)} required value={resourceId}><option value="">Select</option>{forms.map(form => <option key={form.id} value={form.id}>{form.name}</option>)}</select></label>
          : <label>{labels.resourceId}<input autoComplete="off" onChange={event => setResourceId(event.currentTarget.value)} required value={resourceId} /></label>)}
        {scopeKind !== "application" && <label>{labels.parentResourceId}<input autoComplete="off" onChange={event => setParentResourceId(event.currentTarget.value)} value={parentResourceId} /></label>}
        <label className="pk-localization__dialog-wide">{labels.source}<textarea onChange={event => setSourcePattern(event.currentTarget.value)} required rows={3} value={sourcePattern} /></label>
        <label>{labels.description}<input onChange={event => setDescription(event.currentTarget.value)} value={description} /></label>
        <label>{labels.context}<input onChange={event => setContext(event.currentTarget.value)} value={context} /></label>
      </div>
      <fieldset><legend>{labels.arguments}</legend>{argumentsList.map((argument, index) => <div className="pk-localization__argument" key={index}>
        <label>{labels.argumentName}<input onChange={event => updateArgument(index, { name: event.currentTarget.value })} required value={argument.name} /></label>
        <label>{labels.argumentType}<select onChange={event => updateArgument(index, { type: event.currentTarget.value as LocalizationArgumentType })} value={argument.type}>{argumentTypes.map(type => <option key={type} value={type}>{type}</option>)}</select></label>
        <label className="pk-localization__argument-required"><input checked={argument.required} onChange={event => updateArgument(index, { required: event.currentTarget.checked })} type="checkbox" /> {labels.required}</label>
        <button aria-label={`${labels.removeArgument} ${index + 1}`} onClick={() => setArgumentsList(current => current.filter((_, position) => position !== index))} type="button">{labels.removeArgument}</button>
      </div>)}<button onClick={() => setArgumentsList(current => [...current, { name: "", type: "string", required: true }])} type="button">{labels.addArgument}</button></fieldset>
      <div {...localizationSlot(appearance, "dialogActions", "pk-localization__dialog-actions")}><button onClick={onCancel} type="button">{labels.cancel}</button><button type="submit">{labels.create}</button></div>
    </form>
  </dialog>;
}

interface ImportMappingRow { readonly id: number; readonly role: string; readonly column: string; }

function LocalizationImportDialog({ labels, forms, maximumBytes, onCancel, onPreview }: { readonly labels: LocalizationManagementLabels; readonly forms: readonly LocalizationFormOption[]; readonly maximumBytes: number; readonly onCancel: () => void; readonly onPreview: (submission: LocalizationImportSubmission) => Promise<void> }): ReactNode {
  const appearance = useLocalizationAppearance();
  const titleId = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const nextMappingId = useRef(2);
  const [file, setFile] = useState<File | undefined>();
  const [format, setFormat] = useState<LocalizationInterchangeFormat>("csv");
  const [mergePolicy, setMergePolicy] = useState<LocalizationMergePolicy>("preserveExisting");
  const [scopeKind, setScopeKind] = useState<LocalizationScopeKind | "">("");
  const [resourceId, setResourceId] = useState("");
  const [parentResourceId, setParentResourceId] = useState("");
  const [targetLocale, setTargetLocale] = useState("");
  const [mappings, setMappings] = useState<readonly ImportMappingRow[]>([{ id: 0, role: "key", column: "key" }, { id: 1, role: "source", column: "source" }]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const element = dialog.current;
    if (element !== null && !element.open) element.showModal();
    return () => { if (element?.open === true) element.close(); };
  }, []);
  const updateMapping = (id: number, update: Partial<ImportMappingRow>) => setMappings(current => current.map(mapping => mapping.id === id ? { ...mapping, ...update } : mapping));
  const selectFile = (selected: File | undefined) => {
    setError(""); setFile(selected);
    if (selected === undefined) return;
    if (selected.size > maximumBytes) setError(`The selected file exceeds the ${maximumBytes}-byte import limit.`);
    const inferred = inferFormat(selected.name);
    if (inferred !== undefined) setFormat(inferred);
  };
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    if (file === undefined) { setError("Select a localization import file."); return; }
    if (file.size < 1 || file.size > maximumBytes) { setError(`The import file must contain between 1 and ${maximumBytes} bytes.`); return; }
    const activeMappings = mappings.filter(mapping => mapping.role.trim().length > 0 || mapping.column.trim().length > 0);
    if (activeMappings.some(mapping => mapping.role.trim().length === 0 || mapping.column.trim().length === 0)) { setError("Each mapping requires both a semantic role and a source column."); return; }
    const roles = activeMappings.map(mapping => mapping.role.trim());
    if (new Set(roles).size !== roles.length) { setError("A semantic import role can be mapped only once."); return; }
    const mapping = Object.fromEntries(activeMappings.map(item => [item.role.trim(), item.column.trim()]));
    if (targetLocale.trim().length > 0) mapping.locale = targetLocale.trim();
    const scope: LocalizationScope | undefined = scopeKind === "" ? undefined : scopeKind === "application" ? { kind: scopeKind } : { kind: scopeKind, resourceId, ...(parentResourceId.trim().length === 0 ? {} : { parentResourceId }) };
    setBusy(true);
    try {
      await onPreview({ format, fileName: file.name, ...(file.type.length === 0 ? {} : { mediaType: file.type }), content: new Uint8Array(await file.arrayBuffer()), mergePolicy, ...(scope === undefined ? {} : { scope }), mapping });
    }
    catch (failure) { setError(failure instanceof Error ? failure.message : "The localization import could not be previewed."); }
    finally { setBusy(false); }
  };
  return <dialog aria-labelledby={titleId} {...localizationSlot(appearance, "dialog", "pk-localization__dialog")} onCancel={event => { event.preventDefault(); if (!busy) onCancel(); }} ref={dialog}>
    <form onSubmit={event => { void submit(event); }}>
      <h2 id={titleId}>{labels.importTitle}</h2>
      {error.length > 0 && <p className="pk-localization__dialog-error" role="alert">{error}</p>}
      <div {...localizationSlot(appearance, "dialogFields", "pk-localization__dialog-fields")}>
        <label className="pk-localization__dialog-wide">{labels.file}<input accept=".csv,.json,.xlsx,.xlf,.xliff,.po" onChange={event => selectFile(event.currentTarget.files?.[0])} required type="file" /></label>
        <label>{labels.format}<select onChange={event => setFormat(event.currentTarget.value as LocalizationInterchangeFormat)} value={format}>{interchangeFormats.map(value => <option key={value} value={value}>{value}</option>)}</select></label>
        <label>{labels.mergePolicy}<select onChange={event => setMergePolicy(event.currentTarget.value as LocalizationMergePolicy)} value={mergePolicy}>{mergePolicies.map(value => <option key={value} value={value}>{value}</option>)}</select></label>
        <label>{labels.scope}<select onChange={event => { const next = event.currentTarget.value as LocalizationScopeKind | ""; setScopeKind(next); if (next === "" || next === "application") { setResourceId(""); setParentResourceId(""); } }} value={scopeKind}><option value="">{labels.importFromFile}</option>{scopeKinds.map(kind => <option key={kind} value={kind}>{kind}</option>)}</select></label>
        {scopeKind !== "" && scopeKind !== "application" && (formScopeKinds.has(scopeKind) && forms.length > 0
          ? <label>{labels.resourceId}<select onChange={event => setResourceId(event.currentTarget.value)} required value={resourceId}><option value="">Select</option>{forms.map(form => <option key={form.id} value={form.id}>{form.name}</option>)}</select></label>
          : <label>{labels.resourceId}<input onChange={event => setResourceId(event.currentTarget.value)} required value={resourceId} /></label>)}
        {scopeKind !== "" && scopeKind !== "application" && <label>{labels.parentResourceId}<input onChange={event => setParentResourceId(event.currentTarget.value)} value={parentResourceId} /></label>}
        <label>{labels.targetLocale}<input onChange={event => setTargetLocale(event.currentTarget.value)} placeholder="nl-NL" value={targetLocale} /></label>
      </div>
      <fieldset><legend>{labels.mappings}</legend>{mappings.map(mapping => <div className="pk-localization__mapping" key={mapping.id}>
        <label>{labels.mappingRole}<input onChange={event => updateMapping(mapping.id, { role: event.currentTarget.value })} value={mapping.role} /></label>
        <label>{labels.mappingColumn}<input onChange={event => updateMapping(mapping.id, { column: event.currentTarget.value })} value={mapping.column} /></label>
        <button aria-label={`${labels.removeMapping} ${mapping.role || mapping.id + 1}`} onClick={() => setMappings(current => current.filter(item => item.id !== mapping.id))} type="button">{labels.removeMapping}</button>
      </div>)}<button onClick={() => setMappings(current => [...current, { id: nextMappingId.current++, role: "", column: "" }])} type="button">{labels.addMapping}</button></fieldset>
      <div {...localizationSlot(appearance, "dialogActions", "pk-localization__dialog-actions")}><button disabled={busy} onClick={onCancel} type="button">{labels.cancel}</button><button disabled={busy} type="submit">{labels.previewImport}</button></div>
    </form>
  </dialog>;
}

function LocalizationRowEditor({ row, labels, canEdit, onCommit }: { readonly row: LocalizationRow; readonly labels: LocalizationManagementLabels; readonly canEdit: boolean; readonly onCommit: (row: LocalizationRow, pattern: string, state: LocalizationValueState) => void }): ReactNode {
  const appearance = useLocalizationAppearance();
  const [pattern, setPattern] = useState(row.pattern ?? "");
  const [state, setState] = useState<LocalizationValueState>(row.state === "missing" ? "draft" : row.state);
  useEffect(() => { setPattern(row.pattern ?? ""); setState(row.state === "missing" ? "draft" : row.state); }, [row]);
  const commit = (nextPattern = pattern, nextState = state) => { if (canEdit && nextPattern.length > 0 && (nextPattern !== (row.pattern ?? "") || nextState !== row.state)) onCommit(row, nextPattern, nextState); };
  return <tr {...localizationSlot(appearance, "row", "pk-localization__row")}><td data-label={labels.key}>{row.key}</td><td className="pk-localization__scope" data-label={labels.scope}>{scopeLabel(row)}</td><td data-label={labels.source}>{row.sourcePattern}</td><td data-label={labels.locale}>{row.languageTag}</td><td data-label={labels.translation}><textarea aria-label={`${labels.translation}: ${row.key} (${row.languageTag})`} dir={row.direction === "rightToLeft" ? "rtl" : row.direction === "leftToRight" ? "ltr" : "auto"} disabled={!canEdit} onBlur={() => commit()} onChange={event => setPattern(event.currentTarget.value)} rows={2} value={pattern} /></td><td data-label={labels.status}><select aria-label={`${labels.status}: ${row.key} (${row.languageTag})`} disabled={!canEdit || pattern.length === 0} onChange={event => { const next = event.currentTarget.value as LocalizationValueState; setState(next); commit(pattern, next); }} value={state}>{valueStates.map(value => <option key={value} value={value}>{value}</option>)}</select></td></tr>;
}

function LocalizationImportReview({ preview, labels, onApply }: { readonly preview: LocalizationImportPreview; readonly labels: LocalizationManagementLabels; readonly onApply: ((previewId: string) => void | Promise<void>) | undefined }): ReactNode {
  const appearance = useLocalizationAppearance();
  const blocking = preview.diagnostics.some(item => item.severity === "error") || preview.changes.some(change => change.kind === "conflict");
  return <section aria-label={labels.importPreview} {...localizationSlot(appearance, "importReview", "pk-localization__import")}><h2>{labels.importPreview}</h2><p>{preview.mergePolicy} · {preview.changes.length} changes</p><ul>{preview.changes.map((change, index) => <li key={`${change.key}-${change.languageTag}-${index}`}>{change.kind}: {change.key} ({change.languageTag})</li>)}</ul>{onApply !== undefined && <button disabled={blocking} onClick={() => { void onApply(preview.previewId); }} type="button">{labels.applyImport}</button>}</section>;
}

function scopeLabel(row: LocalizationRow): string { return row.scope.resourceId === undefined || row.scope.resourceId === null ? row.scope.kind : `${row.scope.kind}:${row.scope.resourceId}`; }

function inferFormat(fileName: string): LocalizationInterchangeFormat | undefined {
  const name = fileName.toLowerCase();
  if (name.endsWith(".csv")) return "csv";
  if (name.endsWith(".xlsx")) return "xlsx";
  if (name.endsWith(".json")) return "json";
  if (name.endsWith(".xlf") || name.endsWith(".xliff")) return "xliff21";
  if (name.endsWith(".po")) return "po";
  return undefined;
}
