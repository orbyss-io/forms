import type {
  JsonFormsRendererRegistryEntry,
  UISchemaElement,
  ValidationMode
} from "@jsonforms/core";
import { JsonForms } from "@jsonforms/react";
import {
  createContext,
  useContext,
  useMemo,
  type ComponentProps,
  type ReactNode
} from "react";
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

export const programKitReactFormsAdapterVersion = "1.0.0";

type JsonFormsAjv = NonNullable<ComponentProps<typeof JsonForms>["ajv"]>;

export interface ProgramKitJsonFormsRuntime {
  readonly schema: JsonObject;
  readonly uiSchema: JsonObject;
  readonly validate: ProgramKitValidator;
  readonly translate: ProgramKitTranslator;
}

export interface ProgramKitJsonFormsProps {
  readonly runtime: ProgramKitJsonFormsRuntime;
  readonly data: JsonValue;
  /** Renderer components are application-owned and must be supplied by the consumer. */
  readonly renderers: readonly JsonFormsRendererRegistryEntry[];
  readonly cells?: Readonly<NonNullable<ComponentProps<typeof JsonForms>["cells"]>>;
  readonly readonly?: boolean;
  readonly config?: unknown;
  /** Errors are calculated but hidden by default until the application requests presentation. */
  readonly validationMode?: ValidationMode;
  readonly onChange?: (data: JsonValue, issues: readonly RuntimeValidationIssue[]) => void;
}

const ProgramKitFormsRuntimeContext = createContext<ProgramKitJsonFormsRuntime | null>(null);

/** Gives application-owned renderers access to the governed runtime ports. */
export function useProgramKitFormsRuntime(): ProgramKitJsonFormsRuntime | null {
  return useContext(ProgramKitFormsRuntimeContext);
}

/**
 * Thin React binding over JSON Forms. Program Kit supplies schema, translation and precompiled
 * validation integration; the consuming application owns every renderer and visual decision.
 */
export function ProgramKitJsonForms({
  runtime,
  data,
  renderers,
  cells,
  readonly,
  config,
  validationMode = "ValidateAndHide",
  onChange
}: ProgramKitJsonFormsProps): ReactNode {
  if (renderers.length === 0) {
    throw new Error("Program Kit's React binding requires consumer-supplied JSON Forms renderers.");
  }
  const ajv = useMemo(
    () => createPrecompiledJsonFormsAjvFacade(runtime.schema, runtime.validate) as unknown as JsonFormsAjv,
    [runtime.schema, runtime.validate]
  );
  const translator = useMemo(() => createJsonFormsTranslatorAdapter(runtime.translate), [runtime.translate]);
  return (
    <ProgramKitFormsRuntimeContext.Provider value={runtime}>
      <JsonForms
        ajv={ajv}
        data={data}
        i18n={{ translate: translator }}
        renderers={[...renderers]}
        schema={runtime.schema}
        uischema={runtime.uiSchema as unknown as UISchemaElement}
        validationMode={validationMode}
        {...(cells === undefined ? {} : { cells: [...cells] })}
        {...(config === undefined ? {} : { config })}
        {...(readonly === undefined ? {} : { readonly })}
        {...(onChange === undefined ? {} : {
          onChange: state => onChange(
            state.data as JsonValue,
            jsonFormsValidationErrorsToIssues(
              (state.errors ?? []) as readonly JsonFormsCompatibleValidationError[]
            )
          )
        })}
      />
    </ProgramKitFormsRuntimeContext.Provider>
  );
}
