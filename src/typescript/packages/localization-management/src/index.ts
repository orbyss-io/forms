export type LocalizationDirection = "leftToRight" | "rightToLeft" | "auto";
export type LocalizationLifecycleState = "draft" | "validated" | "inReview" | "approved" | "published" | "retired";
export type LocalizationValueState = "draft" | "machineSuggested" | "reviewed" | "approved";
export type LocalizationScopeKind = "application" | "feature" | "form" | "formValidation" | "custom";
export type LocalizationArgumentType = "string" | "number" | "integer" | "date" | "dateTime" | "time" | "select";

export interface LocalizationActor { readonly id: string; readonly kind: string; readonly displayName?: string; }
export interface LocalizationLocale { readonly languageTag: string; readonly direction: LocalizationDirection; readonly fallbackLanguageTag?: string | null; readonly requiredForPublication: boolean; }
export interface LocalizationScope { readonly kind: LocalizationScopeKind; readonly resourceId?: string | null; readonly parentResourceId?: string | null; }
export interface LocalizationArgument { readonly name: string; readonly type: LocalizationArgumentType; readonly required: boolean; }
export interface LocalizationValue { readonly languageTag: string; readonly pattern: string; readonly state: LocalizationValueState; readonly provenance?: string | null; readonly updatedAt?: string | null; readonly updatedBy?: LocalizationActor | null; }
export interface LocalizationMessage { readonly key: string; readonly scope: LocalizationScope; readonly sourcePattern: string; readonly arguments: readonly LocalizationArgument[]; readonly values: readonly LocalizationValue[]; readonly description?: string | null; readonly context?: string | null; }
export interface LocalizationDocument {
  readonly id: string;
  readonly revision: number;
  readonly version: string;
  readonly name: string;
  readonly sourceLocale: string;
  readonly state: LocalizationLifecycleState;
  readonly locales: readonly LocalizationLocale[];
  readonly messages: readonly LocalizationMessage[];
  readonly metadata?: Readonly<Record<string, string>> | null;
}

export interface LocalizationDiagnostic { readonly code: string; readonly severity: "information" | "warning" | "error"; readonly message: string; readonly key?: string; readonly languageTag?: string; }
export interface LocalizationFilters { readonly locale?: string; readonly scopeKind?: LocalizationScopeKind; readonly formId?: string; readonly state?: LocalizationValueState | "missing"; readonly missingOnly?: boolean; readonly text?: string; }
export interface LocalizationRow {
  readonly id: string;
  readonly key: string;
  readonly scope: LocalizationScope;
  readonly sourcePattern: string;
  readonly languageTag: string;
  readonly direction: LocalizationDirection;
  readonly pattern?: string;
  readonly state: LocalizationValueState | "missing";
  readonly provenance?: string | null;
}
export interface LocalizationRowWindow { readonly rows: readonly LocalizationRow[]; readonly first: number; readonly total: number; readonly hasPrevious: boolean; readonly hasNext: boolean; }

export type LocalizationOperation =
  | { readonly type: "setValue"; readonly key: string; readonly scope: LocalizationScope; readonly value: LocalizationValue }
  | { readonly type: "removeValue"; readonly key: string; readonly scope: LocalizationScope; readonly languageTag: string }
  | { readonly type: "addMessage"; readonly message: LocalizationMessage }
  | { readonly type: "removeMessage"; readonly key: string; readonly scope: LocalizationScope };
export interface LocalizationCommand { readonly commandId: string; readonly expectedSequence: number; readonly actor: LocalizationActor; readonly requestedAt: string; readonly operations: readonly LocalizationOperation[]; }
export interface LocalizationSnapshot { readonly document: LocalizationDocument; readonly sequence: number; readonly canUndo: boolean; readonly canRedo: boolean; }

export class LocalizationConcurrencyError extends Error {
  public constructor(public readonly expected: number, public readonly actual: number) {
    super(`The localization command expected sequence ${expected}, but the current sequence is ${actual}.`);
    this.name = "LocalizationConcurrencyError";
  }
}
export class LocalizationValidationError extends Error {
  public constructor(public readonly diagnostics: readonly LocalizationDiagnostic[]) {
    super(diagnostics.map(item => `${item.code}: ${item.message}`).join("\n"));
    this.name = "LocalizationValidationError";
  }
}

export class LocalizationManagementSession {
  #document: LocalizationDocument;
  #sequence = 0;
  #undo: LocalizationDocument[] = [];
  #redo: LocalizationDocument[] = [];
  readonly #commands = new Map<string, string>();
  public constructor(document: LocalizationDocument, readonly maximumHistory = 100) {
    if (!Number.isSafeInteger(maximumHistory) || maximumHistory < 1) throw new Error("Localization history limit must be a positive safe integer.");
    this.#document = validated(document);
  }
  public snapshot(): LocalizationSnapshot { return Object.freeze({ document: this.#document, sequence: this.#sequence, canUndo: this.#undo.length > 0, canRedo: this.#redo.length > 0 }); }
  public apply(command: LocalizationCommand): LocalizationSnapshot {
    requirePortable(command.commandId, "command ID"); requirePortable(command.actor.id, "actor ID"); requirePortable(command.actor.kind, "actor kind");
    if (!Number.isFinite(Date.parse(command.requestedAt))) throw new Error("A localization command requires an ISO audit timestamp.");
    if (command.operations.length === 0) throw new Error("A localization command requires at least one operation.");
    const fingerprint = JSON.stringify({ actor: command.actor, requestedAt: command.requestedAt, operations: command.operations });
    const previous = this.#commands.get(command.commandId);
    if (previous !== undefined) {
      if (previous !== fingerprint) throw new Error(`Command ID '${command.commandId}' was reused with different audit data or operations.`);
      return this.snapshot();
    }
    if (command.expectedSequence !== this.#sequence) throw new LocalizationConcurrencyError(command.expectedSequence, this.#sequence);
    let next = this.#document;
    for (const operation of command.operations) next = applyOperation(next, operation);
    next = validated(next);
    this.#undo.push(this.#document); if (this.#undo.length > this.maximumHistory) this.#undo.shift();
    this.#document = next; this.#redo = []; this.#sequence += 1; this.#commands.set(command.commandId, fingerprint);
    return this.snapshot();
  }
  public undo(): LocalizationSnapshot { const previous = this.#undo.pop(); if (previous === undefined) return this.snapshot(); this.#redo.push(this.#document); this.#document = previous; this.#sequence += 1; return this.snapshot(); }
  public redo(): LocalizationSnapshot { const next = this.#redo.pop(); if (next === undefined) return this.snapshot(); this.#undo.push(this.#document); this.#document = next; this.#sequence += 1; return this.snapshot(); }
}

export function projectLocalizationRows(document: LocalizationDocument, filters: LocalizationFilters = {}, first = 0, maximum = 50): LocalizationRowWindow {
  if (!Number.isSafeInteger(first) || first < 0 || !Number.isSafeInteger(maximum) || maximum < 1 || maximum > 200) throw new Error("Localization row windows require first >= 0 and maximum between 1 and 200.");
  const localeMap = new Map(document.locales.map(locale => [locale.languageTag.toLowerCase(), locale]));
  const rows: LocalizationRow[] = [];
  for (const message of document.messages) {
    if (filters.scopeKind !== undefined && message.scope.kind !== filters.scopeKind) continue;
    if (filters.formId !== undefined && (!formScopeKinds.has(message.scope.kind) || message.scope.resourceId !== filters.formId)) continue;
    const values = new Map(message.values.map(value => [value.languageTag.toLowerCase(), value]));
    for (const locale of document.locales) {
      if (locale.languageTag.toLowerCase() === document.sourceLocale.toLowerCase()) continue;
      if (filters.locale !== undefined && locale.languageTag.toLowerCase() !== filters.locale.toLowerCase()) continue;
      const value = values.get(locale.languageTag.toLowerCase());
      const state = value?.state ?? "missing";
      if (filters.missingOnly === true && state !== "missing") continue;
      if (filters.state !== undefined && state !== filters.state) continue;
      const haystack = `${message.key}\n${message.sourcePattern}\n${value?.pattern ?? ""}\n${message.scope.resourceId ?? ""}`.toLocaleLowerCase();
      if (filters.text !== undefined && filters.text.trim().length > 0 && !haystack.includes(filters.text.trim().toLocaleLowerCase())) continue;
      rows.push(Object.freeze({ id: rowId(message.scope, message.key, locale.languageTag), key: message.key, scope: message.scope, sourcePattern: message.sourcePattern, languageTag: locale.languageTag, direction: localeMap.get(locale.languageTag.toLowerCase())?.direction ?? "auto", ...(value === undefined ? {} : { pattern: value.pattern, provenance: value.provenance }), state }));
    }
  }
  rows.sort((left, right) => scopeIdentity(left.scope).localeCompare(scopeIdentity(right.scope)) || left.key.localeCompare(right.key) || left.languageTag.localeCompare(right.languageTag));
  const safeFirst = Math.min(first, Math.max(0, rows.length - 1));
  return Object.freeze({ rows: Object.freeze(rows.slice(safeFirst, safeFirst + maximum)), first: safeFirst, total: rows.length, hasPrevious: safeFirst > 0, hasNext: safeFirst + maximum < rows.length });
}

export function validateLocalizationDocument(document: LocalizationDocument): readonly LocalizationDiagnostic[] {
  const diagnostics: LocalizationDiagnostic[] = [];
  const add = (code: string, message: string, key?: string, languageTag?: string, severity: LocalizationDiagnostic["severity"] = "error") => diagnostics.push({ code, severity, message, ...(key === undefined ? {} : { key }), ...(languageTag === undefined ? {} : { languageTag }) });
  if (!portable(document.id) || document.name.trim().length === 0 || !Number.isSafeInteger(document.revision) || document.revision < 1 || document.version.trim().length === 0) add("PKLM001", "Catalog identity, name, positive revision, and concurrency version are required.");
  const locales = new Map<string, LocalizationLocale>();
  for (const locale of document.locales) {
    const normalized = locale.languageTag.toLowerCase();
    if (!validLocale(locale.languageTag) || locales.has(normalized)) add("PKLM010", `Locale '${locale.languageTag}' is invalid or duplicated.`, undefined, locale.languageTag);
    locales.set(normalized, locale);
  }
  if (!locales.has(document.sourceLocale.toLowerCase())) add("PKLM011", "Source locale must be declared.", undefined, document.sourceLocale);
  for (const locale of document.locales) if (locale.fallbackLanguageTag !== undefined && locale.fallbackLanguageTag !== null && !locales.has(locale.fallbackLanguageTag.toLowerCase())) add("PKLM012", `Fallback locale '${locale.fallbackLanguageTag}' is not declared.`, undefined, locale.languageTag);
  const identities = new Set<string>();
  for (const message of document.messages) {
    const identity = `${scopeIdentity(message.scope)}:${message.key}`;
    if (!portable(message.key) || identities.has(identity)) add("PKLM020", `Message '${message.key}' is invalid or duplicated in its scope.`, message.key);
    identities.add(identity);
    if (message.scope.kind === "application" ? message.scope.resourceId != null : !portable(message.scope.resourceId ?? "")) add("PKLM021", "Message scope ownership is invalid.", message.key);
    const args = new Map<string, LocalizationArgument>();
    for (const argument of message.arguments) { if (!argumentName(argument.name) || args.has(argument.name)) add("PKLM022", `Argument '${argument.name}' is invalid or duplicated.`, message.key); args.set(argument.name, argument); }
    validatePattern(message.sourcePattern, args, add, message.key, document.sourceLocale);
    const valueLocales = new Set<string>();
    for (const value of message.values) {
      const normalized = value.languageTag.toLowerCase();
      if (!locales.has(normalized) || valueLocales.has(normalized)) add("PKLM023", `Value locale '${value.languageTag}' is undeclared or duplicated.`, message.key, value.languageTag);
      valueLocales.add(normalized); validatePattern(value.pattern, args, add, message.key, value.languageTag);
    }
    for (const locale of document.locales.filter(item => item.requiredForPublication && item.languageTag.toLowerCase() !== document.sourceLocale.toLowerCase())) if (!valueLocales.has(locale.languageTag.toLowerCase())) add("PKLM024", `Required locale '${locale.languageTag}' is missing.`, message.key, locale.languageTag, "warning");
  }
  return Object.freeze(diagnostics.map(item => Object.freeze(item)));
}

export type LocalizationMergePolicy = "addOnly" | "preserveExisting" | "replaceImported" | "replaceScope";
export type LocalizationInterchangeFormat = "csv" | "xlsx" | "json" | "xliff21" | "po";
export interface LocalizationImportSubmission {
  readonly format: LocalizationInterchangeFormat;
  readonly fileName: string;
  readonly mediaType?: string;
  readonly content: Uint8Array;
  readonly mergePolicy: LocalizationMergePolicy;
  readonly scope?: LocalizationScope;
  readonly mapping: Readonly<Record<string, string>>;
}
export type LocalizationImportChangeKind = "add" | "replace" | "preserve" | "remove" | "conflict";
export interface LocalizationImportChange { readonly key: string; readonly languageTag: string; readonly scope: LocalizationScope; readonly kind: LocalizationImportChangeKind; readonly existingPattern?: string | null; readonly importedPattern?: string | null; }
export interface LocalizationImportPreview { readonly previewId: string; readonly contentSha256: string; readonly basedOnRevision: number; readonly mergePolicy: LocalizationMergePolicy; readonly changes: readonly LocalizationImportChange[]; readonly diagnostics: readonly LocalizationDiagnostic[]; }

function applyOperation(document: LocalizationDocument, operation: LocalizationOperation): LocalizationDocument {
  if (operation.type === "addMessage") {
    if (document.messages.some(item => `${scopeIdentity(item.scope)}:${item.key}` === `${scopeIdentity(operation.message.scope)}:${operation.message.key}`)) throw new Error(`Message '${operation.message.key}' already exists in its scope.`);
    return { ...document, messages: [...document.messages, operation.message] };
  }
  const identity = `${scopeIdentity(operation.scope)}:${operation.key}`;
  if (operation.type === "removeMessage") return { ...document, messages: document.messages.filter(item => `${scopeIdentity(item.scope)}:${item.key}` !== identity) };
  let found = false;
  const messages = document.messages.map(message => {
    if (`${scopeIdentity(message.scope)}:${message.key}` !== identity) return message;
    found = true;
    if (operation.type === "removeValue") return { ...message, values: message.values.filter(value => value.languageTag.toLowerCase() !== operation.languageTag.toLowerCase()) };
    const index = message.values.findIndex(value => value.languageTag.toLowerCase() === operation.value.languageTag.toLowerCase());
    return { ...message, values: index < 0 ? [...message.values, operation.value] : message.values.map((value, position) => position === index ? operation.value : value) };
  });
  if (!found) throw new Error(`Message '${operation.key}' does not exist in its scope.`);
  return { ...document, messages };
}

function validatePattern(pattern: string, args: ReadonlyMap<string, LocalizationArgument>, add: (code: string, message: string, key?: string, languageTag?: string, severity?: LocalizationDiagnostic["severity"]) => void, key: string, locale: string): void {
  if (pattern.trim().length === 0 || pattern.length > 16_384) { add("PKLM030", "Message pattern is empty or exceeds the safe limit.", key, locale); return; }
  let balance = 0; for (const character of pattern) { if (character === "{") balance += 1; else if (character === "}") balance -= 1; if (balance < 0) break; }
  if (balance !== 0) add("PKLM031", "Message pattern contains unmatched braces.", key, locale);
  for (const match of pattern.matchAll(/\{\s*([A-Za-z_][A-Za-z0-9_]*)(?:\s*,\s*(plural|selectordinal|select))?\s*(?=,|\})/g)) {
    const name = match[1] as string; const format = match[2]; const argument = args.get(name);
    if (argument === undefined) add("PKLM032", `Pattern argument '${name}' is not declared.`, key, locale);
    if ((format === "plural" || format === "selectordinal") && argument !== undefined && argument.type !== "integer" && argument.type !== "number") add("PKLM033", `Plural argument '${name}' must be numeric.`, key, locale);
    if (format !== undefined && !/\bother\s*\{/.test(pattern.slice(match.index ?? 0))) add("PKLM034", `The '${format}' argument requires an other branch.`, key, locale);
  }
}

function validated(document: LocalizationDocument): LocalizationDocument { const clone = JSON.parse(JSON.stringify(document)) as LocalizationDocument; const errors = validateLocalizationDocument(clone).filter(item => item.severity === "error"); if (errors.length > 0) throw new LocalizationValidationError(errors); return deepFreeze(clone); }
function rowId(scope: LocalizationScope, key: string, locale: string): string { return `${scopeIdentity(scope)}:${key}:${locale}`; }
function scopeIdentity(scope: LocalizationScope): string { return `${scope.kind}:${scope.parentResourceId ?? ""}:${scope.resourceId ?? ""}`; }
function requirePortable(value: string, name: string): void { if (!portable(value)) throw new Error(`Localization ${name} must be a portable identifier.`); }
function portable(value: string): boolean { return /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value); }
function argumentName(value: string): boolean { return /^[A-Za-z_][A-Za-z0-9_]{0,127}$/.test(value); }
function validLocale(value: string): boolean { return /^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$/.test(value); }
function deepFreeze<T>(value: T): T { if (typeof value === "object" && value !== null && !Object.isFrozen(value)) { Object.freeze(value); for (const nested of Object.values(value)) deepFreeze(nested); } return value; }
const formScopeKinds = new Set<LocalizationScopeKind>(["form", "formValidation"]);
