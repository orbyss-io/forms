import { and, optionIs, rankWith, uiTypeIs, type ControlProps, type JsonFormsRendererRegistryEntry, type RankedTester } from "@jsonforms/core";
import { useJsonForms, withJsonFormsControlProps } from "@jsonforms/react";
import { useEffect, useMemo, useReducer, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import type { JsonPrimitive, JsonValue } from "@orbyss/program-kit-forms-contracts";
import { FormLookupController, FormLookupRegistry, type FormLookupItem } from "@orbyss/program-kit-forms-lookups";

export const programKitSearchableSelectComponentId = "ProgramKit.SearchableSelect";
export const programKitSearchableSelectVersion = "1.0.0";

export interface ProgramKitLookupReactConfig {
  readonly registry: FormLookupRegistry;
  readonly locale: string;
  readonly loadingLabel?: string;
  readonly noResultsLabel?: string;
  readonly loadMoreLabel?: string;
  readonly clearLabel?: string;
}

interface SearchableSelectOptions {
  readonly dataSourceId: string;
  readonly minimumCharacters: number;
  readonly debounceMilliseconds: number;
  readonly pageSize?: number;
  readonly filterBindings: Readonly<Record<string, string>>;
}

function SearchableSelectRendererComponent(props: ControlProps): ReactNode {
  const jsonForms = useJsonForms();
  const configuration = trustedLookupConfiguration(props.config);
  const options = parseOptions(props.uischema.options);
  const [, rerender] = useReducer(value => value + 1, 0);
  const controller = useMemo(() => new FormLookupController({
    registry: configuration.registry,
    dataSourceId: options.dataSourceId,
    locale: configuration.locale,
    minimumCharacters: options.minimumCharacters,
    debounceMilliseconds: options.debounceMilliseconds,
    ...(options.pageSize === undefined ? {} : { pageSize: options.pageSize }),
    onChange: () => rerender()
  }), [configuration.registry, configuration.locale, options.dataSourceId, options.minimumCharacters, options.debounceMilliseconds, options.pageSize]);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedLabel, setSelectedLabel] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const resolveGeneration = useRef(0);
  const listboxId = `${props.id}-lookup-listbox`;
  const statusId = `${props.id}-lookup-status`;
  const errorId = `${props.id}-lookup-error`;
  const snapshot = controller.snapshot();
  const primitiveData = isPrimitive(props.data) ? props.data : undefined;
  const filters = useMemo(
    () => resolveFilters(options.filterBindings, jsonForms.core?.data as JsonValue | undefined),
    [options.filterBindings, jsonForms.core?.data]
  );

  useEffect(() => () => { controller.cancel(); }, [controller]);
  useEffect(() => {
    const generation = ++resolveGeneration.current;
    if (primitiveData === undefined || primitiveData === null) {
      setSelectedLabel("");
      return;
    }
    void controller.resolve([primitiveData]).then(items => {
      if (resolveGeneration.current === generation) setSelectedLabel(items[0]?.label ?? String(primitiveData));
    }).catch(() => {
      if (resolveGeneration.current === generation) setSelectedLabel(String(primitiveData));
    });
  }, [controller, primitiveData]);

  if (!props.visible) return null;
  const choose = (item: FormLookupItem) => {
    if (item.disabled) return;
    props.handleChange(props.path, item.value);
    setSelectedLabel(item.label);
    setSearch("");
    setOpen(false);
    setActiveIndex(-1);
  };
  const runSearch = (value: string) => {
    setSearch(value);
    setOpen(true);
    setActiveIndex(-1);
    void controller.search(value, filters);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") { setOpen(false); setActiveIndex(-1); return; }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      if (snapshot.items.length === 0) return;
      const direction = event.key === "ArrowDown" ? 1 : -1;
      setActiveIndex(index => (index + direction + snapshot.items.length) % snapshot.items.length);
    } else if (event.key === "Enter" && open && activeIndex >= 0) {
      event.preventDefault();
      const item = snapshot.items[activeIndex];
      if (item !== undefined) choose(item);
    }
  };
  const describedBy = [props.description === undefined ? undefined : `${props.id}-description`, props.errors.length === 0 ? undefined : errorId, statusId].filter(Boolean).join(" ");

  return (
    <div className="pk-searchable-select">
      <label className="pk-searchable-select__label" htmlFor={props.id}>{props.label}{props.required ? " *" : ""}</label>
      {props.description !== undefined && <p id={`${props.id}-description`}>{props.description}</p>}
      <div className="pk-searchable-select__input-row">
        <input
          aria-activedescendant={activeIndex < 0 ? undefined : optionId(props.id, activeIndex)}
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-describedby={describedBy}
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-invalid={props.errors.length > 0}
          autoComplete="off"
          disabled={!props.enabled}
          id={props.id}
          onBlur={() => setOpen(false)}
          onChange={event => runSearch(event.currentTarget.value)}
          onFocus={() => { if (search.length >= options.minimumCharacters) setOpen(true); }}
          onKeyDown={onKeyDown}
          role="combobox"
          value={search.length > 0 || open ? search : selectedLabel}
        />
        {primitiveData !== undefined && primitiveData !== null && (
          <button
            aria-label={configuration.clearLabel ?? `Clear ${props.label}`}
            disabled={!props.enabled}
            onClick={() => { props.handleChange(props.path, undefined); setSelectedLabel(""); setSearch(""); }}
            type="button"
          >×</button>
        )}
      </div>
      {open && snapshot.items.length > 0 && (
        <ul className="pk-searchable-select__listbox" id={listboxId} role="listbox">
          {snapshot.items.map((item, index) => (
            <li
              aria-disabled={item.disabled || undefined}
              aria-selected={index === activeIndex}
              className="pk-searchable-select__option"
              data-active={index === activeIndex || undefined}
              id={optionId(props.id, index)}
              key={`${typeof item.value}:${String(item.value)}`}
              onMouseDown={event => { event.preventDefault(); choose(item); }}
              role="option"
            >
              <span>{item.label}</span>
              {item.description !== undefined && <small>{item.description}</small>}
            </li>
          ))}
          {snapshot.nextCursor !== undefined && (
            <li className="pk-searchable-select__more">
              <button onMouseDown={event => event.preventDefault()} onClick={() => { void controller.loadMore(); }} type="button">
                {configuration.loadMoreLabel ?? "Load more"}
              </button>
            </li>
          )}
        </ul>
      )}
      <p aria-live="polite" className="pk-searchable-select__status" id={statusId}>
        {snapshot.status === "loading" || snapshot.status === "debouncing"
          ? configuration.loadingLabel ?? "Loading options"
          : open && snapshot.status === "ready" && snapshot.items.length === 0
            ? configuration.noResultsLabel ?? "No options found"
            : ""}
      </p>
      {snapshot.failure !== undefined && <p className="pk-searchable-select__failure" role="alert">{snapshot.failure.message}</p>}
      {props.errors.length > 0 && <p className="pk-searchable-select__error" id={errorId}>{props.errors}</p>}
    </div>
  );
}

export const programKitSearchableSelectTester: RankedTester = rankWith(
  1100,
  and(uiTypeIs("Control"), optionIs("component", programKitSearchableSelectComponentId))
);

export const ProgramKitSearchableSelectRenderer = withJsonFormsControlProps(SearchableSelectRendererComponent);
export const programKitSearchableSelectRendererEntry: JsonFormsRendererRegistryEntry = Object.freeze({
  tester: programKitSearchableSelectTester,
  renderer: ProgramKitSearchableSelectRenderer
});

function trustedLookupConfiguration(value: unknown): ProgramKitLookupReactConfig {
  if (!isRecord(value) || !isRecord(value.programKitLookups) || !(value.programKitLookups.registry instanceof FormLookupRegistry) || typeof value.programKitLookups.locale !== "string") {
    throw new Error("The searchable-select renderer requires a trusted Program Kit lookup registry and locale.");
  }
  return value.programKitLookups as unknown as ProgramKitLookupReactConfig;
}

function parseOptions(value: unknown): SearchableSelectOptions {
  if (!isRecord(value) || value.component !== programKitSearchableSelectComponentId || !isRecord(value.componentOptions)) throw new Error("Searchable-select component options are missing.");
  const source = value.componentOptions;
  if (typeof source.dataSourceId !== "string") throw new Error("Searchable select requires a dataSourceId.");
  const bindings: Record<string, string> = {};
  for (const [key, binding] of Object.entries(source)) if (key.startsWith("filter.") && typeof binding === "string") bindings[key.slice(7)] = binding;
  return Object.freeze({
    dataSourceId: source.dataSourceId,
    minimumCharacters: integerOption(source.minimumCharacters, 2),
    debounceMilliseconds: integerOption(source.debounceMilliseconds, 250),
    ...(source.pageSize === undefined ? {} : { pageSize: integerOption(source.pageSize, 25) }),
    filterBindings: Object.freeze(bindings)
  });
}

function resolveFilters(bindings: Readonly<Record<string, string>>, data: JsonValue | undefined): Readonly<Record<string, JsonPrimitive>> {
  const filters: Record<string, JsonPrimitive> = {};
  for (const [filter, pointer] of Object.entries(bindings)) {
    const value = readPointer(data, pointer);
    if (isPrimitive(value)) filters[filter] = value;
  }
  return Object.freeze(filters);
}

function readPointer(data: JsonValue | undefined, pointer: string): JsonValue | undefined {
  if (data === undefined || !pointer.startsWith("/")) throw new Error("Lookup filter bindings must be rooted data JSON Pointers.");
  let current: JsonValue | undefined = data;
  for (const encoded of pointer.slice(1).split("/")) {
    const segment = encoded.replaceAll("~1", "/").replaceAll("~0", "~");
    if (Array.isArray(current)) {
      const index = Number.parseInt(segment, 10);
      current = Number.isSafeInteger(index) ? current[index] : undefined;
    } else if (isRecord(current)) current = current[segment] as JsonValue | undefined;
    else return undefined;
  }
  return current;
}

function integerOption(value: unknown, fallback: number): number {
  if (value === undefined) return fallback;
  const parsed = typeof value === "number" ? value : typeof value === "string" ? Number.parseInt(value, 10) : Number.NaN;
  if (!Number.isSafeInteger(parsed) || parsed < 0) throw new Error("Searchable-select numeric option is invalid.");
  return parsed;
}

function isPrimitive(value: unknown): value is JsonPrimitive { return value === null || ["string", "number", "boolean"].includes(typeof value); }
function optionId(controlId: string, index: number): string { return `${controlId}-lookup-option-${index}`; }
function isRecord(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
