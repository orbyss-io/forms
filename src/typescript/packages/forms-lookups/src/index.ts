import type { JsonPrimitive } from "@orbyss-io/forms-contracts";

export interface FormLookupContract {
  readonly dataSourceId: string;
  readonly contractVersion: string;
  readonly displayName: string;
  readonly providerPackage?: string;
  readonly execution: "public-client" | "server";
  readonly supportsSearch: boolean;
  readonly supportsPaging: boolean;
  readonly filterKeys: readonly string[];
  readonly maximumPageSize: number;
}

export interface FormLookupItem {
  readonly value: JsonPrimitive;
  readonly label: string;
  readonly description?: string;
  readonly disabled?: boolean;
}

export interface FormLookupQuery {
  readonly dataSourceId: string;
  readonly search: string;
  readonly pageSize: number;
  readonly filters: Readonly<Record<string, JsonPrimitive>>;
  readonly cursor?: string;
}

export interface FormLookupPage {
  readonly items: readonly FormLookupItem[];
  readonly nextCursor?: string;
}

export interface FormLookupContext {
  readonly signal: AbortSignal;
  readonly locale: string;
}

export interface FormLookupProvider {
  readonly contract: FormLookupContract;
  readonly search: (query: FormLookupQuery, context: FormLookupContext) => Promise<FormLookupPage>;
  readonly resolve: (values: readonly JsonPrimitive[], context: FormLookupContext) => Promise<readonly FormLookupItem[]>;
}

export interface FormLookupLimits {
  readonly maximumSearchLength: number;
  readonly maximumFilterCount: number;
  readonly maximumLabelLength: number;
  readonly maximumDescriptionLength: number;
  readonly maximumCursorLength: number;
  readonly maximumResolveValues: number;
}

export const defaultFormLookupLimits: FormLookupLimits = Object.freeze({
  maximumSearchLength: 256,
  maximumFilterCount: 16,
  maximumLabelLength: 512,
  maximumDescriptionLength: 2_048,
  maximumCursorLength: 2_048,
  maximumResolveValues: 100
});

export class FormLookupRegistry {
  readonly #providers: ReadonlyMap<string, FormLookupProvider>;
  readonly #limits: FormLookupLimits;

  public constructor(providers: readonly FormLookupProvider[], limits: Partial<FormLookupLimits> = {}) {
    this.#limits = Object.freeze({ ...defaultFormLookupLimits, ...limits });
    const map = new Map<string, FormLookupProvider>();
    for (const provider of providers) {
      validateContract(provider.contract);
      if (map.has(provider.contract.dataSourceId)) throw new Error(`Duplicate lookup provider '${provider.contract.dataSourceId}'.`);
      map.set(provider.contract.dataSourceId, provider);
    }
    this.#providers = map;
  }

  public list(): readonly FormLookupContract[] {
    return Object.freeze([...this.#providers.values()].map(provider => deepFreeze(clone(provider.contract))));
  }

  public require(dataSourceId: string): FormLookupContract {
    return this.#provider(dataSourceId).contract;
  }

  public async search(query: FormLookupQuery, context: FormLookupContext): Promise<FormLookupPage> {
    const provider = this.#provider(query.dataSourceId);
    validateQuery(query, provider.contract, this.#limits);
    context.signal.throwIfAborted();
    const page = await provider.search(deepFreeze(clone(query)), context);
    context.signal.throwIfAborted();
    return validatePage(page, query.pageSize, this.#limits);
  }

  public async resolve(dataSourceId: string, values: readonly JsonPrimitive[], context: FormLookupContext): Promise<readonly FormLookupItem[]> {
    if (values.length > this.#limits.maximumResolveValues) throw new Error("Lookup resolution value limit exceeded.");
    const provider = this.#provider(dataSourceId);
    context.signal.throwIfAborted();
    const items = await provider.resolve(Object.freeze([...values]), context);
    context.signal.throwIfAborted();
    const validated = validateItems(items, values.length, this.#limits);
    const requested = new Set(values.map(valueIdentity));
    if (validated.some(item => !requested.has(valueIdentity(item.value)))) throw new Error("Lookup resolution returned an unrequested value.");
    return validated;
  }

  #provider(dataSourceId: string): FormLookupProvider {
    const provider = this.#providers.get(dataSourceId);
    if (provider === undefined) throw new Error(`Lookup provider '${dataSourceId}' is not registered.`);
    return provider;
  }
}

export type FormLookupStatus = "idle" | "debouncing" | "loading" | "ready" | "failed";
export interface FormLookupFailure { readonly code: string; readonly message: string; readonly retryable: boolean; }
export interface FormLookupSnapshot {
  readonly search: string;
  readonly status: FormLookupStatus;
  readonly items: readonly FormLookupItem[];
  readonly nextCursor?: string;
  readonly failure?: FormLookupFailure;
}

export interface FormLookupControllerOptions {
  readonly registry: FormLookupRegistry;
  readonly dataSourceId: string;
  readonly locale: string;
  readonly minimumCharacters?: number;
  readonly debounceMilliseconds?: number;
  readonly pageSize?: number;
  readonly onChange?: (snapshot: FormLookupSnapshot) => void;
}

export class FormLookupController {
  readonly #options: Required<Pick<FormLookupControllerOptions, "minimumCharacters" | "debounceMilliseconds" | "pageSize">> & FormLookupControllerOptions;
  #snapshot: FormLookupSnapshot = Object.freeze({ search: "", status: "idle", items: Object.freeze([]) });
  #abort: AbortController | undefined;
  #filters: Readonly<Record<string, JsonPrimitive>> = Object.freeze({});

  public constructor(options: FormLookupControllerOptions) {
    const contract = options.registry.require(options.dataSourceId);
    const pageSize = options.pageSize ?? Math.min(25, contract.maximumPageSize);
    if (!Number.isSafeInteger(pageSize) || pageSize < 1 || pageSize > contract.maximumPageSize) throw new Error("Lookup page size is outside the provider contract.");
    this.#options = { ...options, minimumCharacters: options.minimumCharacters ?? 2, debounceMilliseconds: options.debounceMilliseconds ?? 250, pageSize };
  }

  public snapshot(): FormLookupSnapshot { return this.#snapshot; }

  public async search(search: string, filters: Readonly<Record<string, JsonPrimitive>> = {}, signal?: AbortSignal): Promise<FormLookupSnapshot> {
    this.cancel();
    this.#filters = deepFreeze(clone(filters));
    if (search.length < this.#options.minimumCharacters) {
      this.#set({ search, status: "idle", items: Object.freeze([]) });
      return this.#snapshot;
    }
    const abort = linkedAbortController(signal);
    this.#abort = abort;
    try {
      this.#set({ search, status: "debouncing", items: Object.freeze([]) });
      await delay(this.#options.debounceMilliseconds, abort.signal);
      this.#set({ search, status: "loading", items: Object.freeze([]) });
      const page = await this.#options.registry.search({
        dataSourceId: this.#options.dataSourceId,
        search,
        pageSize: this.#options.pageSize,
        filters: this.#filters
      }, { signal: abort.signal, locale: this.#options.locale });
      this.#set({ search, status: "ready", items: page.items, ...(page.nextCursor === undefined ? {} : { nextCursor: page.nextCursor }) });
    } catch (error) {
      if (!abort.signal.aborted) this.#set({ search, status: "failed", items: Object.freeze([]), failure: publicFailure(error) });
    } finally {
      if (this.#abort === abort) this.#abort = undefined;
    }
    return this.#snapshot;
  }

  public async loadMore(signal?: AbortSignal): Promise<FormLookupSnapshot> {
    if (this.#snapshot.nextCursor === undefined || this.#snapshot.status !== "ready") return this.#snapshot;
    const cursor = this.#snapshot.nextCursor;
    this.cancel();
    const abort = linkedAbortController(signal);
    this.#abort = abort;
    const previous = this.#snapshot;
    try {
      this.#set({ ...previous, status: "loading" });
      const page = await this.#options.registry.search({
        dataSourceId: this.#options.dataSourceId,
        search: previous.search,
        pageSize: this.#options.pageSize,
        filters: this.#filters,
        cursor
      }, { signal: abort.signal, locale: this.#options.locale });
      const known = new Set(previous.items.map(item => valueIdentity(item.value)));
      const items = Object.freeze([...previous.items, ...page.items.filter(item => !known.has(valueIdentity(item.value)))]);
      this.#set({ search: previous.search, status: "ready", items, ...(page.nextCursor === undefined ? {} : { nextCursor: page.nextCursor }) });
    } catch (error) {
      if (!abort.signal.aborted) this.#set({ ...previous, status: "failed", failure: publicFailure(error) });
    } finally {
      if (this.#abort === abort) this.#abort = undefined;
    }
    return this.#snapshot;
  }

  public async resolve(values: readonly JsonPrimitive[], signal?: AbortSignal): Promise<readonly FormLookupItem[]> {
    const abort = linkedAbortController(signal);
    try {
      return await this.#options.registry.resolve(this.#options.dataSourceId, values, { signal: abort.signal, locale: this.#options.locale });
    } catch (error) {
      if (abort.signal.aborted) throw new DOMException("Aborted", "AbortError");
      const failure = publicFailure(error);
      throw new FormLookupPublicError(failure.code, failure.message, failure.retryable);
    }
  }

  public cancel(): boolean {
    if (this.#abort === undefined) return false;
    this.#abort.abort();
    this.#abort = undefined;
    this.#set({
      search: this.#snapshot.search,
      status: "idle",
      items: this.#snapshot.items,
      ...(this.#snapshot.nextCursor === undefined ? {} : { nextCursor: this.#snapshot.nextCursor })
    });
    return true;
  }

  #set(snapshot: FormLookupSnapshot): void {
    this.#snapshot = deepFreeze(clone(snapshot));
    this.#options.onChange?.(this.#snapshot);
  }
}

function validateContract(contract: FormLookupContract): void {
  if (!validId(contract.dataSourceId)) throw new Error("Lookup data-source ID must be portable.");
  if (!/^\d+\.\d+\.\d+$/.test(contract.contractVersion)) throw new Error(`Lookup '${contract.dataSourceId}' requires a semantic contract version.`);
  if (contract.displayName.trim().length === 0) throw new Error(`Lookup '${contract.dataSourceId}' requires a display name.`);
  if (!Number.isSafeInteger(contract.maximumPageSize) || contract.maximumPageSize < 1 || contract.maximumPageSize > 500) throw new Error(`Lookup '${contract.dataSourceId}' has an invalid page limit.`);
  if (new Set(contract.filterKeys).size !== contract.filterKeys.length || contract.filterKeys.some(key => !validId(key))) throw new Error(`Lookup '${contract.dataSourceId}' has invalid filter keys.`);
}

function validateQuery(query: FormLookupQuery, contract: FormLookupContract, limits: FormLookupLimits): void {
  if (query.search.length > limits.maximumSearchLength) throw new Error("Lookup search length limit exceeded.");
  if (!contract.supportsSearch && query.search.length > 0) throw new Error(`Lookup '${contract.dataSourceId}' does not support search.`);
  if (!Number.isSafeInteger(query.pageSize) || query.pageSize < 1 || query.pageSize > contract.maximumPageSize) throw new Error("Lookup page size is outside the provider contract.");
  const filterKeys = Object.keys(query.filters);
  if (filterKeys.length > limits.maximumFilterCount || filterKeys.some(key => !contract.filterKeys.includes(key))) throw new Error("Lookup query contains an undeclared filter.");
  if (query.cursor !== undefined && (!contract.supportsPaging || query.cursor.length > limits.maximumCursorLength)) throw new Error("Lookup cursor is outside the provider contract.");
}

function validatePage(page: FormLookupPage, maximumItems: number, limits: FormLookupLimits): FormLookupPage {
  const items = validateItems(page.items, maximumItems, limits);
  if (page.nextCursor !== undefined && page.nextCursor.length > limits.maximumCursorLength) throw new Error("Lookup cursor length limit exceeded.");
  return Object.freeze({ items, ...(page.nextCursor === undefined ? {} : { nextCursor: page.nextCursor }) });
}

function validateItems(items: readonly FormLookupItem[], maximumItems: number, limits: FormLookupLimits): readonly FormLookupItem[] {
  if (!Array.isArray(items) || items.length > maximumItems) throw new Error("Lookup response item limit exceeded.");
  const ids = new Set<string>();
  for (const item of items) {
    if (item.value === null || !["string", "number", "boolean"].includes(typeof item.value)) throw new Error("Lookup item value must be a non-null JSON primitive.");
    if (item.label.length === 0 || item.label.length > limits.maximumLabelLength) throw new Error("Lookup item label is outside the configured limits.");
    if (item.description !== undefined && item.description.length > limits.maximumDescriptionLength) throw new Error("Lookup item description length limit exceeded.");
    const id = valueIdentity(item.value);
    if (ids.has(id)) throw new Error("Lookup response contains duplicate values.");
    ids.add(id);
  }
  return deepFreeze(clone(items));
}

function publicFailure(error: unknown): FormLookupFailure {
  return error instanceof FormLookupPublicError
    ? { code: error.code, message: error.message, retryable: error.retryable }
    : { code: "PKLU999", message: "Options could not be loaded.", retryable: true };
}

export class FormLookupPublicError extends Error {
  public constructor(public readonly code: string, message: string, public readonly retryable = true) { super(message); this.name = "FormLookupPublicError"; }
}

function linkedAbortController(signal?: AbortSignal): AbortController {
  const abort = new AbortController();
  if (signal?.aborted) abort.abort(signal.reason);
  else signal?.addEventListener("abort", () => abort.abort(signal.reason), { once: true });
  return abort;
}

function delay(milliseconds: number, signal: AbortSignal): Promise<void> {
  if (!Number.isFinite(milliseconds) || milliseconds < 0 || milliseconds > 10_000) throw new Error("Lookup debounce is outside the supported range.");
  if (signal.aborted) return Promise.reject(new DOMException("Aborted", "AbortError"));
  if (milliseconds === 0) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, milliseconds);
    signal.addEventListener("abort", () => { clearTimeout(timer); reject(new DOMException("Aborted", "AbortError")); }, { once: true });
  });
}

function valueIdentity(value: JsonPrimitive): string { return `${typeof value}:${String(value)}`; }
function validId(value: string): boolean { return /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value); }
function clone<T>(value: T): T { return JSON.parse(JSON.stringify(value)) as T; }
function deepFreeze<T>(value: T): T { if (typeof value === "object" && value !== null && !Object.isFrozen(value)) { Object.freeze(value); for (const nested of Object.values(value)) deepFreeze(nested); } return value; }
