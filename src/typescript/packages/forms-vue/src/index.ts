import { computed, defineComponent, h, type PropType } from "vue";
import { JsonForms, rendererProps, useJsonFormsControl, type ControlProps } from "@jsonforms/vue";
import {
  and,
  optionIs,
  rankWith,
  schemaMatches,
  uiTypeIs,
  type ControlElement,
  type RankedTester
} from "@jsonforms/core";
import type {
  JsonFormsCellRendererRegistryEntry,
  JsonFormsRendererRegistryEntry,
  UISchemaElement,
  ValidationMode
} from "@jsonforms/core";
import type {
  JsonObject,
  JsonValue,
  ProgramKitTranslator,
  ProgramKitValidator,
  RuntimeValidationIssue
} from "@orbyss/program-kit-forms-contracts";
import {
  createJsonFormsTranslatorAdapter,
  createPrecompiledJsonFormsAjvFacade,
  jsonFormsValidationErrorsToIssues,
  type JsonFormsCompatibleValidationError
} from "@orbyss/program-kit-forms-jsonforms-runtime";

export const programKitVueFormsAdapterVersion = "1.0.0";

export interface ProgramKitJsonFormsVueRuntime {
  readonly schema: JsonObject;
  readonly uiSchema: JsonObject;
  readonly validate: ProgramKitValidator;
  readonly translate: ProgramKitTranslator;
}

export interface ProgramKitJsonFormsVueChange {
  readonly data: JsonValue;
  readonly issues: readonly RuntimeValidationIssue[];
}

const coreRendererRank = 5;
const specializedCoreRendererRank = 10;
type ChoiceValue = string | number | boolean | null;
type VueControlState = ReturnType<typeof useJsonFormsControl>["control"]["value"];
type VueHandleChange = ReturnType<typeof useJsonFormsControl>["handleChange"];

interface TrustedControlOptions {
  readonly multi: boolean;
  readonly placeholder?: string;
  readonly rows: number;
  readonly autocomplete?: string;
  readonly enumLabels: readonly string[];
}

function createControlRenderer(
  name: string,
  render: (control: VueControlState, handleChange: VueHandleChange) => ReturnType<typeof h> | null
) {
  return defineComponent({
    name,
    props: rendererProps<ControlElement>(),
    setup(props) {
      const binding = useJsonFormsControl(props as unknown as ControlProps);
      return () => render(binding.control.value, binding.handleChange);
    }
  });
}

function renderControlFrame(control: VueControlState, input: ReturnType<typeof h>): ReturnType<typeof h> | null {
  if (!control.visible) return null;
  const description = typeof control.description === "string" ? control.description : "";
  const descriptionId = description.length > 0 ? `${control.id}-description` : undefined;
  const errorId = control.errors.length > 0 ? `${control.id}-error` : undefined;
  return h("div", { class: "pk-form-control", "data-control-path": control.path }, [
    h("label", { class: "pk-form-control__label", for: control.id }, [
      control.label,
      ...(control.required ? [h("span", { "aria-hidden": "true" }, " *")] : [])
    ]),
    ...(descriptionId === undefined ? [] : [h("p", { class: "pk-form-control__description", id: descriptionId }, description)]),
    h("div", { class: "pk-form-control__input" }, [input]),
    ...(errorId === undefined ? [] : [h("p", { class: "pk-form-control__error", id: errorId, role: "alert" }, control.errors)])
  ]);
}

export const ProgramKitVueTextControl = createControlRenderer("ProgramKitVueTextControl", (control, handleChange) => {
  const options = trustedControlOptions(control.uischema);
  return renderControlFrame(control, h("input", {
    "aria-describedby": controlDescriptionIds(control),
    "aria-invalid": control.errors.length > 0 || undefined,
    autocomplete: options.autocomplete,
    disabled: !control.enabled,
    id: control.id,
    maxlength: finiteInteger(control.schema.maxLength),
    minlength: finiteInteger(control.schema.minLength),
    onInput: (event: Event) => handleChange(control.path, inputElement(event).value),
    placeholder: options.placeholder,
    readonly: schemaIsReadOnly(control.schema),
    required: control.required,
    type: inputTypeForFormat(control.schema.format),
    value: typeof control.data === "string" ? control.data : ""
  }));
});

export const ProgramKitVueMultilineControl = createControlRenderer("ProgramKitVueMultilineControl", (control, handleChange) => {
  const options = trustedControlOptions(control.uischema);
  return renderControlFrame(control, h("textarea", {
    "aria-describedby": controlDescriptionIds(control),
    "aria-invalid": control.errors.length > 0 || undefined,
    disabled: !control.enabled,
    id: control.id,
    maxlength: finiteInteger(control.schema.maxLength),
    minlength: finiteInteger(control.schema.minLength),
    onInput: (event: Event) => handleChange(control.path, inputElement(event).value),
    placeholder: options.placeholder,
    readonly: schemaIsReadOnly(control.schema),
    required: control.required,
    rows: options.rows,
    value: typeof control.data === "string" ? control.data : ""
  }));
});

export const ProgramKitVueNumberControl = createControlRenderer("ProgramKitVueNumberControl", (control, handleChange) => {
  const integer = control.schema.type === "integer";
  return renderControlFrame(control, h("input", {
    "aria-describedby": controlDescriptionIds(control),
    "aria-invalid": control.errors.length > 0 || undefined,
    disabled: !control.enabled,
    id: control.id,
    inputmode: "decimal",
    max: finiteNumber(control.schema.maximum),
    min: finiteNumber(control.schema.minimum),
    onInput: (event: Event) => {
      const value = inputElement(event).value;
      handleChange(control.path, value === "" ? undefined : Number(value));
    },
    readonly: schemaIsReadOnly(control.schema),
    required: control.required,
    step: integer ? 1 : "any",
    type: "number",
    value: typeof control.data === "number" && Number.isFinite(control.data) ? control.data : ""
  }));
});

export const ProgramKitVueBooleanControl = createControlRenderer("ProgramKitVueBooleanControl", (control, handleChange) => {
  if (!control.visible) return null;
  const description = typeof control.description === "string" ? control.description : "";
  const descriptionId = description.length > 0 ? `${control.id}-description` : undefined;
  const errorId = control.errors.length > 0 ? `${control.id}-error` : undefined;
  return h("div", { class: "pk-form-control pk-form-control--boolean", "data-control-path": control.path }, [
    h("label", { class: "pk-form-control__boolean" }, [
      h("input", {
        "aria-describedby": controlDescriptionIds(control),
        "aria-invalid": control.errors.length > 0 || undefined,
        checked: control.data === true,
        disabled: !control.enabled,
        id: control.id,
        onChange: (event: Event) => handleChange(control.path, inputElement(event).checked),
        required: control.required,
        type: "checkbox"
      }),
      h("span", control.label)
    ]),
    ...(descriptionId === undefined ? [] : [h("p", { class: "pk-form-control__description", id: descriptionId }, description)]),
    ...(errorId === undefined ? [] : [h("p", { class: "pk-form-control__error", id: errorId, role: "alert" }, control.errors)])
  ]);
});

export const ProgramKitVueChoiceControl = createControlRenderer("ProgramKitVueChoiceControl", (control, handleChange) => {
  const choices = primitiveChoices(control.schema.enum);
  const labels = trustedControlOptions(control.uischema).enumLabels;
  return renderControlFrame(control, h("select", {
    "aria-describedby": controlDescriptionIds(control),
    "aria-invalid": control.errors.length > 0 || undefined,
    disabled: !control.enabled,
    id: control.id,
    onChange: (event: Event) => handleChange(control.path, choices.find(choice => choiceKey(choice) === inputElement(event).value)),
    required: control.required,
    value: choiceKey(control.data)
  }, [
    h("option", { value: "" }, "Select"),
    ...choices.map((choice, index) => h("option", { key: choiceKey(choice), value: choiceKey(choice) }, labels[index] ?? String(choice ?? "None")))
  ]));
});

export const ProgramKitVueMultiChoiceControl = createControlRenderer("ProgramKitVueMultiChoiceControl", (control, handleChange) => {
  const itemSchema = isRecord(control.schema.items) ? control.schema.items : {};
  const choices = primitiveChoices(itemSchema.enum);
  const labels = trustedControlOptions(control.uischema).enumLabels;
  const selected = new Set((Array.isArray(control.data) ? control.data : []).map(choiceKey));
  return renderControlFrame(control, h("select", {
    "aria-describedby": controlDescriptionIds(control),
    "aria-invalid": control.errors.length > 0 || undefined,
    disabled: !control.enabled,
    id: control.id,
    multiple: true,
    onChange: (event: Event) => handleChange(control.path, [...inputElement(event).selectedOptions]
      .map(option => choices.find(choice => choiceKey(choice) === option.value))
      .filter((value): value is ChoiceValue => value !== undefined)),
    required: control.required,
    value: [...selected]
  }, choices.map((choice, index) => h("option", { key: choiceKey(choice), value: choiceKey(choice) }, labels[index] ?? String(choice ?? "None")))));
});

export const programKitVueMultilineControlTester: RankedTester = rankWith(specializedCoreRendererRank, and(
  uiTypeIs("Control"),
  schemaMatches(schema => schema.type === "string"),
  optionIs("multi", true)
));
export const programKitVueChoiceControlTester: RankedTester = rankWith(specializedCoreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => Array.isArray(schema.enum))));
export const programKitVueMultiChoiceControlTester: RankedTester = rankWith(specializedCoreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => schema.type === "array" && isRecord(schema.items) && Array.isArray(schema.items.enum))));
export const programKitVueBooleanControlTester: RankedTester = rankWith(coreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => schema.type === "boolean")));
export const programKitVueNumberControlTester: RankedTester = rankWith(coreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => schema.type === "number" || schema.type === "integer")));
export const programKitVueTextControlTester: RankedTester = rankWith(coreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => schema.type === "string")));

export const programKitVueCoreRendererEntries: readonly JsonFormsRendererRegistryEntry[] = Object.freeze([
  Object.freeze({ tester: programKitVueMultilineControlTester, renderer: ProgramKitVueMultilineControl }),
  Object.freeze({ tester: programKitVueMultiChoiceControlTester, renderer: ProgramKitVueMultiChoiceControl }),
  Object.freeze({ tester: programKitVueChoiceControlTester, renderer: ProgramKitVueChoiceControl }),
  Object.freeze({ tester: programKitVueBooleanControlTester, renderer: ProgramKitVueBooleanControl }),
  Object.freeze({ tester: programKitVueNumberControlTester, renderer: ProgramKitVueNumberControl }),
  Object.freeze({ tester: programKitVueTextControlTester, renderer: ProgramKitVueTextControl })
]);

/**
 * Vue binding for the governed Program Kit runtime. Validation remains precompiled and UI-schema
 * conditions use the same bounded interpreter as every other framework adapter.
 */
export const ProgramKitJsonFormsVue = defineComponent({
  name: "ProgramKitJsonFormsVue",
  props: {
    runtime: {
      type: Object as PropType<ProgramKitJsonFormsVueRuntime>,
      required: true
    },
    data: {
      type: [Object, Array, String, Number, Boolean] as PropType<JsonValue>,
      required: true
    },
    renderers: {
      type: Array as PropType<readonly JsonFormsRendererRegistryEntry[]>,
      default: () => []
    },
    cells: {
      type: Array as PropType<readonly JsonFormsCellRendererRegistryEntry[]>,
      default: undefined
    },
    readonly: {
      type: Boolean,
      default: false
    },
    config: {
      type: Object as PropType<Readonly<Record<string, unknown>>>,
      default: undefined
    },
    validationMode: {
      type: String as PropType<ValidationMode>,
      default: "ValidateAndHide"
    }
  },
  emits: {
    change: (change: ProgramKitJsonFormsVueChange) => change !== null
  },
  setup(props, { emit }) {
    const ajv = computed(() => createPrecompiledJsonFormsAjvFacade(
      props.runtime.schema,
      props.runtime.validate
    ));
    const translator = computed(() => createJsonFormsTranslatorAdapter(props.runtime.translate));
    return () => h(JsonForms, {
      ajv: ajv.value as never,
      data: props.data,
      renderers: [...programKitVueCoreRendererEntries, ...props.renderers],
      schema: props.runtime.schema,
      uischema: props.runtime.uiSchema as unknown as UISchemaElement,
      readonly: props.readonly,
      validationMode: props.validationMode,
      i18n: {
        translate: translator.value
      },
      ...(props.cells === undefined ? {} : { cells: [...props.cells] }),
      ...(props.config === undefined ? {} : { config: props.config }),
      onChange: (state: { readonly data: unknown; readonly errors?: readonly JsonFormsCompatibleValidationError[] }) => emit("change", {
        data: state.data as JsonValue,
        issues: jsonFormsValidationErrorsToIssues(state.errors ?? [])
      })
    });
  }
});

const allowedAutocomplete = new Set(["off", "on", "name", "email", "username", "new-password", "current-password", "organization", "street-address", "postal-code", "country", "tel", "url"]);

function trustedControlOptions(uiSchema: UISchemaElement): TrustedControlOptions {
  const raw = isRecord(uiSchema) && isRecord(uiSchema.options) ? uiSchema.options : {};
  const placeholder = typeof raw.placeholder === "string" && raw.placeholder.length <= 500 ? raw.placeholder : undefined;
  const autocomplete = typeof raw.autocomplete === "string" && allowedAutocomplete.has(raw.autocomplete) ? raw.autocomplete : undefined;
  const rows = typeof raw.rows === "number" && Number.isSafeInteger(raw.rows) ? Math.min(30, Math.max(2, raw.rows)) : 5;
  const enumLabels = Array.isArray(raw.enumLabels) ? raw.enumLabels.filter((value): value is string => typeof value === "string" && value.length <= 500) : [];
  return Object.freeze({ multi: raw.multi === true, rows, enumLabels: Object.freeze(enumLabels), ...(placeholder === undefined ? {} : { placeholder }), ...(autocomplete === undefined ? {} : { autocomplete }) });
}

function controlDescriptionIds(control: VueControlState): string | undefined {
  const values = [
    typeof control.description === "string" && control.description.length > 0 ? `${control.id}-description` : undefined,
    control.errors.length > 0 ? `${control.id}-error` : undefined
  ];
  return values.filter((value): value is string => value !== undefined).join(" ") || undefined;
}

function inputTypeForFormat(format: string | undefined): "text" | "email" | "url" | "date" | "time" {
  return format === "email" ? "email" : format === "uri" || format === "url" ? "url" : format === "date" ? "date" : format === "time" ? "time" : "text";
}

function primitiveChoices(value: unknown): readonly ChoiceValue[] {
  return Array.isArray(value) ? value.filter((item): item is ChoiceValue => item === null || ["string", "number", "boolean"].includes(typeof item)) : [];
}

function choiceKey(value: unknown): string {
  return value === undefined ? "" : JSON.stringify(value);
}

function finiteNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function finiteInteger(value: unknown): number | undefined {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : undefined;
}

function schemaIsReadOnly(value: unknown): boolean {
  return isRecord(value) && value.readOnly === true;
}

function inputElement(event: Event): HTMLInputElement & HTMLSelectElement & HTMLTextAreaElement {
  return event.currentTarget as HTMLInputElement & HTMLSelectElement & HTMLTextAreaElement;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
