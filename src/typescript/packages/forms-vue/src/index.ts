import { computed, defineComponent, h, type PropType } from "vue";
import { JsonForms } from "@jsonforms/vue";
import type {
  JsonFormsCellRendererRegistryEntry,
  JsonFormsRendererRegistryEntry,
  UISchemaElement,
  ValidationMode
} from "@jsonforms/core";
import type {
  JsonObject,
  JsonValue,
  OrbyssTranslator,
  OrbyssValidator,
  RuntimeValidationIssue
} from "@orbyss-io/forms-contracts";
import {
  createJsonFormsTranslatorAdapter,
  createPrecompiledJsonFormsAjvFacade,
  jsonFormsValidationErrorsToIssues,
  type JsonFormsCompatibleValidationError
} from "@orbyss-io/forms-jsonforms-runtime";

export const programKitVueFormsAdapterVersion = "1.0.0";

export interface OrbyssJsonFormsVueRuntime {
  readonly schema: JsonObject;
  readonly uiSchema: JsonObject;
  readonly validate: OrbyssValidator;
  readonly translate: OrbyssTranslator;
}

export interface OrbyssJsonFormsVueChange {
  readonly data: JsonValue;
  readonly issues: readonly RuntimeValidationIssue[];
}

/**
 * Thin Vue binding over JSON Forms. Renderer components and styling are application-owned and must
 * be supplied by the consumer.
 */
export const OrbyssJsonFormsVue = defineComponent({
  name: "OrbyssJsonFormsVue",
  props: {
    runtime: {
      type: Object as PropType<OrbyssJsonFormsVueRuntime>,
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
    },
    validationMode: {
      type: String as PropType<ValidationMode>,
      default: "ValidateAndHide"
    }
  },
  emits: {
    change: (change: OrbyssJsonFormsVueChange) => change !== null
  },
  setup(props, { emit }) {
    if (props.renderers.length === 0) {
      throw new Error("Orbyss Forms's Vue binding requires consumer-supplied JSON Forms renderers.");
    }
    const ajv = computed(() => createPrecompiledJsonFormsAjvFacade(
      props.runtime.schema,
      props.runtime.validate
    ));
    const translator = computed(() => createJsonFormsTranslatorAdapter(props.runtime.translate));
    return () => h(JsonForms, {
      ajv: ajv.value as never,
      data: props.data,
      renderers: [...props.renderers],
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
