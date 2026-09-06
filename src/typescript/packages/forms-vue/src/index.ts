import { computed, defineComponent, h, type PropType } from "vue";
import { JsonForms } from "@jsonforms/vue";
import type {
  JsonFormsCellRendererRegistryEntry,
  JsonFormsRendererRegistryEntry,
  UISchemaElement
} from "@jsonforms/core";
import type {
  JsonObject,
  JsonValue,
  ProgramKitTranslator,
  ProgramKitValidator,
  RuntimeValidationIssue
} from "@orbyss/program-kit-forms-contracts";
import {
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
      required: true
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
    return () => h(JsonForms, {
      ajv: ajv.value as never,
      data: props.data,
      renderers: [...props.renderers],
      schema: props.runtime.schema,
      uischema: props.runtime.uiSchema as unknown as UISchemaElement,
      readonly: props.readonly,
      i18n: {
        translate: (key: string, fallback?: string) => props.runtime.translate(key, fallback ?? "")
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
