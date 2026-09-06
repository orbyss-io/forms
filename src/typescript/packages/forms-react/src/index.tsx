import {
  and,
  isVisible,
  optionIs,
  rankWith,
  schemaMatches,
  uiTypeIs,
  type ControlProps,
  type JsonFormsRendererRegistryEntry,
  type LayoutProps,
  type RankedTester,
  type UISchemaElement
} from "@jsonforms/core";
import {
  JsonFormsDispatch,
  JsonForms,
  useJsonForms,
  withJsonFormsControlProps,
  withJsonFormsLayoutProps
} from "@jsonforms/react";
import {
  createContext,
  useEffect,
  useContext,
  useMemo,
  useReducer,
  useRef,
  type ComponentProps,
  type KeyboardEvent,
  type ReactNode
} from "react";
import type {
  FormActionRequirement,
  FormIconReference,
  JsonObject,
  JsonValue,
  ProgramKitTranslator,
  ProgramKitValidator,
  RuntimeValidationIssue
} from "@orbyss/program-kit-forms-contracts";
import {
  ProgramKitActionController,
  parseProgramKitActionBar,
  type ActionAvailability,
  type ProgramKitActionDefinition,
  type ProgramKitActionResult,
  type ProgramKitActionSnapshot
} from "@orbyss/program-kit-forms-actions";
import {
  ProgramKitWizardController,
  parseProgramKitWizard,
  type ProgramKitWizardDefinition,
  type WizardIconReference,
  type WizardSnapshot,
  type WizardStepDefinition,
  type WizardStepStatus,
  type WizardValidationIssue
} from "@orbyss/program-kit-forms-wizard";
import {
  createPrecompiledJsonFormsAjvFacade,
  jsonFormsValidationErrorsToIssues,
  type JsonFormsCompatibleValidationError
} from "@orbyss/program-kit-forms-jsonforms-runtime";

export const programKitReactFormsAdapterVersion = "1.0.0";

const coreRendererRank = 5;
const specializedCoreRendererRank = 10;

type JsonFormsAjv = NonNullable<ComponentProps<typeof JsonForms>["ajv"]>;

export interface ProgramKitJsonFormsRuntime {
  readonly schema: JsonObject;
  readonly uiSchema: JsonObject;
  readonly validate: ProgramKitValidator;
  readonly translate: ProgramKitTranslator;
  readonly actions?: readonly FormActionRequirement[];
  readonly dispatchAction?: (
    actionId: string,
    payload: JsonValue,
    context: { readonly signal: AbortSignal }
  ) => Promise<JsonValue>;
}

export interface ProgramKitJsonFormsProps {
  readonly runtime: ProgramKitJsonFormsRuntime;
  readonly data: JsonValue;
  readonly renderers?: readonly JsonFormsRendererRegistryEntry[];
  readonly cells?: Readonly<NonNullable<ComponentProps<typeof JsonForms>["cells"]>>;
  readonly readonly?: boolean;
  readonly config?: unknown;
  readonly onChange?: (data: JsonValue, issues: readonly RuntimeValidationIssue[]) => void;
}

const ProgramKitFormsRuntimeContext = createContext<ProgramKitJsonFormsRuntime | null>(null);

/** Gives custom Program Kit renderers reactive access to translation and validation ports. */
export function useProgramKitFormsRuntime(): ProgramKitJsonFormsRuntime | null {
  return useContext(ProgramKitFormsRuntimeContext);
}

/**
 * Hosts JSON Forms with a precompiled validator. The supplied facade never turns schema text into
 * executable code in the browser; rule conditions use the framework-neutral bounded portable subset.
 */
export function ProgramKitJsonForms({
  runtime,
  data,
  renderers = [],
  cells,
  readonly,
  config,
  onChange
}: ProgramKitJsonFormsProps): ReactNode {
  const ajv = useMemo(
    () => createPrecompiledJsonFormsAjvFacade(runtime.schema, runtime.validate) as unknown as JsonFormsAjv,
    [runtime.schema, runtime.validate]
  );
  const rendererEntries = useMemo(
    () => [programKitWizardRendererEntry, programKitActionBarRendererEntry, ...programKitCoreRendererEntries, ...renderers],
    [renderers]
  );
  return (
    <ProgramKitFormsRuntimeContext.Provider value={runtime}>
      <JsonForms
        ajv={ajv}
        data={data}
        i18n={{ translate: (key, fallback) => runtime.translate(key, fallback ?? "") }}
        renderers={rendererEntries}
        schema={runtime.schema}
        uischema={runtime.uiSchema as unknown as UISchemaElement}
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

type ChoiceValue = string | number | boolean | null;

interface TrustedControlOptions {
  readonly multi: boolean;
  readonly placeholder?: string;
  readonly rows: number;
  readonly autocomplete?: string;
  readonly enumLabels: readonly string[];
}

function ProgramKitControlFrame({ props, children }: { readonly props: ControlProps; readonly children: ReactNode }): ReactNode {
  if (!props.visible) return null;
  const description = typeof props.description === "string" ? props.description : "";
  const descriptionId = description.length > 0 ? `${props.id}-description` : undefined;
  const errorId = props.errors.length > 0 ? `${props.id}-error` : undefined;
  const describedBy = [descriptionId, errorId].filter((value): value is string => value !== undefined).join(" ") || undefined;
  return <div className="pk-form-control" data-control-path={props.path}>
    <label className="pk-form-control__label" htmlFor={props.id}>{props.label}{props.required && <span aria-hidden="true"> *</span>}</label>
    {descriptionId !== undefined && <p className="pk-form-control__description" id={descriptionId}>{description}</p>}
    <div className="pk-form-control__input" data-described-by={describedBy}>{children}</div>
    {errorId !== undefined && <p className="pk-form-control__error" id={errorId} role="alert">{props.errors}</p>}
  </div>;
}

function ProgramKitTextControlComponent(props: ControlProps): ReactNode {
  const options = trustedControlOptions(props.uischema);
  const inputType = inputTypeForFormat(props.schema.format);
  const describedBy = controlDescriptionIds(props);
  return <ProgramKitControlFrame props={props}><input
    aria-describedby={describedBy}
    aria-invalid={props.errors.length > 0 || undefined}
    autoComplete={options.autocomplete}
    disabled={!props.enabled}
    id={props.id}
    maxLength={finiteInteger(props.schema.maxLength)}
    minLength={finiteInteger(props.schema.minLength)}
    onChange={event => props.handleChange(props.path, event.currentTarget.value)}
    placeholder={options.placeholder}
    readOnly={schemaIsReadOnly(props.schema)}
    required={props.required}
    type={inputType}
    value={typeof props.data === "string" ? props.data : ""}
  /></ProgramKitControlFrame>;
}

function ProgramKitMultilineControlComponent(props: ControlProps): ReactNode {
  const options = trustedControlOptions(props.uischema);
  return <ProgramKitControlFrame props={props}><textarea
    aria-describedby={controlDescriptionIds(props)}
    aria-invalid={props.errors.length > 0 || undefined}
    disabled={!props.enabled}
    id={props.id}
    maxLength={finiteInteger(props.schema.maxLength)}
    minLength={finiteInteger(props.schema.minLength)}
    onChange={event => props.handleChange(props.path, event.currentTarget.value)}
    placeholder={options.placeholder}
    readOnly={schemaIsReadOnly(props.schema)}
    required={props.required}
    rows={options.rows}
    value={typeof props.data === "string" ? props.data : ""}
  /></ProgramKitControlFrame>;
}

function ProgramKitNumberControlComponent(props: ControlProps): ReactNode {
  const integer = props.schema.type === "integer";
  return <ProgramKitControlFrame props={props}><input
    aria-describedby={controlDescriptionIds(props)}
    aria-invalid={props.errors.length > 0 || undefined}
    disabled={!props.enabled}
    id={props.id}
    inputMode="decimal"
    max={finiteNumber(props.schema.maximum)}
    min={finiteNumber(props.schema.minimum)}
    onChange={event => props.handleChange(props.path, event.currentTarget.value === "" ? undefined : Number(event.currentTarget.value))}
    readOnly={schemaIsReadOnly(props.schema)}
    required={props.required}
    step={integer ? 1 : "any"}
    type="number"
    value={typeof props.data === "number" && Number.isFinite(props.data) ? props.data : ""}
  /></ProgramKitControlFrame>;
}

function ProgramKitBooleanControlComponent(props: ControlProps): ReactNode {
  if (!props.visible) return null;
  const errorId = props.errors.length > 0 ? `${props.id}-error` : undefined;
  const description = typeof props.description === "string" ? props.description : "";
  const descriptionId = description.length > 0 ? `${props.id}-description` : undefined;
  const describedBy = [descriptionId, errorId].filter((value): value is string => value !== undefined).join(" ") || undefined;
  return <div className="pk-form-control pk-form-control--boolean" data-control-path={props.path}>
    <label className="pk-form-control__boolean"><input
      aria-describedby={describedBy}
      aria-invalid={props.errors.length > 0 || undefined}
      checked={props.data === true}
      disabled={!props.enabled}
      id={props.id}
      onChange={event => props.handleChange(props.path, event.currentTarget.checked)}
      required={props.required}
      type="checkbox"
    /><span>{props.label}</span></label>
    {descriptionId !== undefined && <p className="pk-form-control__description" id={descriptionId}>{description}</p>}
    {errorId !== undefined && <p className="pk-form-control__error" id={errorId} role="alert">{props.errors}</p>}
  </div>;
}

function ProgramKitChoiceControlComponent(props: ControlProps): ReactNode {
  const choices = primitiveChoices(props.schema.enum);
  const labels = trustedControlOptions(props.uischema).enumLabels;
  const selected = choiceKey(props.data);
  return <ProgramKitControlFrame props={props}><select
    aria-describedby={controlDescriptionIds(props)}
    aria-invalid={props.errors.length > 0 || undefined}
    disabled={!props.enabled}
    id={props.id}
    onChange={event => props.handleChange(props.path, choices.find(choice => choiceKey(choice) === event.currentTarget.value))}
    required={props.required}
    value={selected}
  >
    <option value="">Select</option>
    {choices.map((choice, index) => <option key={choiceKey(choice)} value={choiceKey(choice)}>{labels[index] ?? String(choice ?? "None")}</option>)}
  </select></ProgramKitControlFrame>;
}

function ProgramKitMultiChoiceControlComponent(props: ControlProps): ReactNode {
  const itemSchema = isRecord(props.schema.items) ? props.schema.items : {};
  const choices = primitiveChoices(itemSchema.enum);
  const labels = trustedControlOptions(props.uischema).enumLabels;
  const selected = new Set((Array.isArray(props.data) ? props.data : []).map(choiceKey));
  return <ProgramKitControlFrame props={props}><select
    aria-describedby={controlDescriptionIds(props)}
    aria-invalid={props.errors.length > 0 || undefined}
    disabled={!props.enabled}
    id={props.id}
    multiple
    onChange={event => props.handleChange(props.path, [...event.currentTarget.selectedOptions].map(option => choices.find(choice => choiceKey(choice) === option.value)).filter((value): value is ChoiceValue => value !== undefined))}
    required={props.required}
    value={[...selected]}
  >
    {choices.map((choice, index) => <option key={choiceKey(choice)} value={choiceKey(choice)}>{labels[index] ?? String(choice ?? "None")}</option>)}
  </select></ProgramKitControlFrame>;
}

export const programKitMultilineControlTester: RankedTester = rankWith(specializedCoreRendererRank, and(
  uiTypeIs("Control"),
  schemaMatches(schema => schema.type === "string"),
  optionIs("multi", true)
));
export const programKitChoiceControlTester: RankedTester = rankWith(specializedCoreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => Array.isArray(schema.enum))));
export const programKitMultiChoiceControlTester: RankedTester = rankWith(specializedCoreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => schema.type === "array" && isRecord(schema.items) && Array.isArray(schema.items.enum))));
export const programKitBooleanControlTester: RankedTester = rankWith(coreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => schema.type === "boolean")));
export const programKitNumberControlTester: RankedTester = rankWith(coreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => schema.type === "number" || schema.type === "integer")));
export const programKitTextControlTester: RankedTester = rankWith(coreRendererRank, and(uiTypeIs("Control"), schemaMatches(schema => schema.type === "string")));

export const ProgramKitTextControl = withJsonFormsControlProps(ProgramKitTextControlComponent);
export const ProgramKitMultilineControl = withJsonFormsControlProps(ProgramKitMultilineControlComponent);
export const ProgramKitNumberControl = withJsonFormsControlProps(ProgramKitNumberControlComponent);
export const ProgramKitBooleanControl = withJsonFormsControlProps(ProgramKitBooleanControlComponent);
export const ProgramKitChoiceControl = withJsonFormsControlProps(ProgramKitChoiceControlComponent);
export const ProgramKitMultiChoiceControl = withJsonFormsControlProps(ProgramKitMultiChoiceControlComponent);

export const programKitCoreRendererEntries: readonly JsonFormsRendererRegistryEntry[] = Object.freeze([
  Object.freeze({ tester: programKitMultilineControlTester, renderer: ProgramKitMultilineControl }),
  Object.freeze({ tester: programKitMultiChoiceControlTester, renderer: ProgramKitMultiChoiceControl }),
  Object.freeze({ tester: programKitChoiceControlTester, renderer: ProgramKitChoiceControl }),
  Object.freeze({ tester: programKitBooleanControlTester, renderer: ProgramKitBooleanControl }),
  Object.freeze({ tester: programKitNumberControlTester, renderer: ProgramKitNumberControl }),
  Object.freeze({ tester: programKitTextControlTester, renderer: ProgramKitTextControl })
]);

const allowedAutocomplete = new Set(["off", "on", "name", "email", "username", "new-password", "current-password", "organization", "street-address", "postal-code", "country", "tel", "url"]);

function trustedControlOptions(uiSchema: UISchemaElement): TrustedControlOptions {
  const raw = isRecord(uiSchema) && isRecord(uiSchema.options) ? uiSchema.options : {};
  const placeholder = typeof raw.placeholder === "string" && raw.placeholder.length <= 500 ? raw.placeholder : undefined;
  const autocomplete = typeof raw.autocomplete === "string" && allowedAutocomplete.has(raw.autocomplete) ? raw.autocomplete : undefined;
  const rows = typeof raw.rows === "number" && Number.isSafeInteger(raw.rows) ? Math.min(30, Math.max(2, raw.rows)) : 5;
  const enumLabels = Array.isArray(raw.enumLabels) ? raw.enumLabels.filter((value): value is string => typeof value === "string" && value.length <= 500) : [];
  return Object.freeze({ multi: raw.multi === true, rows, enumLabels: Object.freeze(enumLabels), ...(placeholder === undefined ? {} : { placeholder }), ...(autocomplete === undefined ? {} : { autocomplete }) });
}

function controlDescriptionIds(props: ControlProps): string | undefined {
  const values = [typeof props.description === "string" && props.description.length > 0 ? `${props.id}-description` : undefined, props.errors.length > 0 ? `${props.id}-error` : undefined];
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

export interface ProgramKitActionReactConfig {
  /** Trusted application policy. This callback is never read from form schema data. */
  readonly availability?: (action: ProgramKitActionDefinition) => ActionAvailability;
  readonly renderIcon?: (icon: FormIconReference, action: ProgramKitActionDefinition) => ReactNode;
  readonly onResult?: (action: ProgramKitActionDefinition, result: ProgramKitActionResult) => void;
}

function ProgramKitActionBarRendererComponent(props: LayoutProps): ReactNode {
  const context = useJsonForms();
  const runtime = useProgramKitFormsRuntime();
  const contextRef = useRef(context);
  contextRef.current = context;
  const configuration = trustedActionConfiguration(props.config);
  const requirements = runtime?.actions;
  if (requirements === undefined || runtime?.dispatchAction === undefined) {
    throw new Error("Program Kit action bars require the immutable action manifest and dispatch port.");
  }
  const definition = useMemo(
    () => parseProgramKitActionBar(props.uischema as unknown as JsonObject, requirements),
    [props.uischema, requirements]
  );
  const [, rerender] = useReducer(value => value + 1, 0);
  const controller = useMemo(() => new ProgramKitActionController(definition, {
    validate: runtime.validate,
    dispatch: (actionId, payload, signal) => runtime.dispatchAction!(actionId, payload, { signal }),
    ...(configuration.availability === undefined ? {} : { availability: configuration.availability }),
    onChange: () => rerender()
  }), [definition, runtime, configuration.availability]);

  if (!props.visible) return null;
  const snapshot = controller.snapshot();
  const running = snapshot.runningActionId !== undefined;
  const invoke = async (action: ProgramKitActionSnapshot) => {
    const data = (contextRef.current.core?.data ?? null) as JsonValue;
    const result = await controller.invoke(action.actionId, data, { data });
    configuration.onResult?.(action, result);
  };

  return (
    <div
      aria-busy={running || undefined}
      className="pk-form-actions"
      data-action-bar-id={definition.id}
    >
      <div className="pk-form-actions__buttons">
        {snapshot.actions.map(action => action.availability === "hidden" ? null : (
          <button
            aria-busy={action.status === "running" || undefined}
            className="pk-form-actions__button"
            data-action-id={action.actionId}
            data-action-kind={String(action.kind)}
            data-status={action.status}
            disabled={!props.enabled || running || action.availability === "disabled"}
            key={action.actionId}
            onClick={() => { void invoke(action); }}
            type="button"
          >
            {action.icon !== undefined && action.icon !== null && configuration.renderIcon !== undefined && (
              <span aria-hidden="true" className="pk-form-actions__icon">
                {configuration.renderIcon(action.icon, action)}
              </span>
            )}
            <span className="pk-form-actions__label">
              {runtime.translate(action.label.key, action.label.defaultText, action.label.context)}
            </span>
          </button>
        ))}
      </div>
      {snapshot.actions.filter(action => action.failure !== undefined).map(action => (
        <p className="pk-form-actions__failure" data-action-id={action.actionId} key={action.actionId} role="alert">
          {action.failure?.message}
        </p>
      ))}
    </div>
  );
}

export const programKitActionBarTester: RankedTester = rankWith(1000, uiTypeIs("ProgramKit.ActionBar"));

export const ProgramKitActionBarRenderer = withJsonFormsLayoutProps(ProgramKitActionBarRendererComponent);

export const programKitActionBarRendererEntry: JsonFormsRendererRegistryEntry = Object.freeze({
  tester: programKitActionBarTester,
  renderer: ProgramKitActionBarRenderer
});

export interface ProgramKitWizardLabels {
  readonly navigation: string;
  readonly progress: string;
  readonly back: string;
  readonly next: string;
  readonly skip: string;
  readonly finish: string;
  readonly status: Readonly<Record<WizardStepStatus, string>>;
}

export interface ProgramKitWizardReactConfig {
  readonly initialStepId?: string;
  readonly labels?: Partial<Omit<ProgramKitWizardLabels, "status">> & {
    readonly status?: Partial<ProgramKitWizardLabels["status"]>;
  };
  readonly renderIcon?: (icon: WizardIconReference, step: WizardStepDefinition) => ReactNode;
  readonly onStepChange?: (stepId: string, snapshot: WizardSnapshot) => void;
  readonly onFinish?: (data: unknown, snapshot: WizardSnapshot) => void | Promise<void>;
}

export interface ProgramKitWizardNavigationProps {
  readonly snapshot: WizardSnapshot;
  readonly definition: ProgramKitWizardDefinition;
  readonly labels?: ProgramKitWizardReactConfig["labels"];
  readonly renderIcon?: ProgramKitWizardReactConfig["renderIcon"];
  readonly translateStep?: (step: WizardStepDefinition) => string;
  readonly onSelect: (stepId: string) => void;
}

const defaultLabels: ProgramKitWizardLabels = Object.freeze({
  navigation: "Form steps",
  progress: "Form completion",
  back: "Back",
  next: "Next",
  skip: "Skip optional step",
  finish: "Finish",
  status: Object.freeze({
    current: "Current step",
    completed: "Completed",
    visited: "Visited",
    upcoming: "Not started",
    warning: "Needs attention",
    error: "Contains errors",
    skipped: "Skipped",
    disabled: "Unavailable"
  })
});

/** Semantic navigation shared by the JSON Forms renderer and consumer design-system adapters. */
export function ProgramKitWizardNavigation({
  snapshot,
  definition,
  labels: labelOverrides,
  renderIcon,
  translateStep,
  onSelect
}: ProgramKitWizardNavigationProps): ReactNode {
  const labels = mergeLabels(labelOverrides);
  return (
    <nav
      aria-label={labels.navigation}
      className="pk-form-wizard__navigation"
      data-placement={definition.navigationPlacement}
      data-progress-style={definition.progressStyle}
    >
      <ol className="pk-form-wizard__steps">
        {snapshot.steps.map(step => (
          <li className="pk-form-wizard__step" data-status={step.status} key={step.id}>
            <button
              aria-controls={step.id === snapshot.currentStepId ? panelId(definition.id, step.id) : undefined}
              aria-current={step.id === snapshot.currentStepId ? "step" : undefined}
              className="pk-form-wizard__step-button"
              disabled={!step.selectable}
              id={stepButtonId(definition.id, step.id)}
              onClick={() => onSelect(step.id)}
              onKeyDown={event => navigateByKeyboard(event, step.id, snapshot, definition.id, onSelect)}
              type="button"
            >
              <span aria-hidden="true" className="pk-form-wizard__step-marker">
                {step.icon !== undefined && renderIcon !== undefined
                  ? renderIcon(step.icon, step)
                  : step.index + 1}
              </span>
              <span className="pk-form-wizard__step-label">{translateStep?.(step) ?? step.label}</span>
              <span className="pk-form-wizard__status">{labels.status[step.status]}</span>
            </button>
          </li>
        ))}
      </ol>
      {definition.progressStyle === "progress" && (
        <progress
          aria-label={labels.progress}
          className="pk-form-wizard__progress"
          max={1}
          value={snapshot.progress}
        />
      )}
    </nav>
  );
}

function ProgramKitWizardRendererComponent(props: LayoutProps): ReactNode {
  const context = useJsonForms();
  const programKitRuntime = useProgramKitFormsRuntime();
  const contextRef = useRef(context);
  contextRef.current = context;
  const configuration = trustedWizardConfiguration(props.config);
  const definition = useMemo(
    () => parseProgramKitWizard(props.uischema as unknown as JsonObject),
    [props.uischema]
  );
  const visibleStepIds = definition.steps
    .filter(step => stepIsVisible(step, context))
    .map(step => step.id);
  const visibilityIdentity = visibleStepIds.join("\u001f");
  const [, rerender] = useReducer(value => value + 1, 0);
  const controller = useMemo(() => new ProgramKitWizardController(definition, {
    ...(configuration.initialStepId === undefined ? {} : { initialStepId: configuration.initialStepId }),
    visibleStepIds,
    validateStep: async stepId => validationIssuesForStep(
      definition.steps.find(step => step.id === stepId),
      (contextRef.current.core?.errors ?? []) as readonly JsonFormsCompatibleValidationError[]
    ),
    onChange: () => rerender()
  }), [definition, configuration.initialStepId]);
  useEffect(() => {
    controller.updateVisibleSteps(visibleStepIds);
  }, [controller, visibilityIdentity]);

  if (!props.visible) return null;
  const snapshot = controller.snapshot();
  const active = snapshot.steps.find(step => step.id === snapshot.currentStepId);
  if (active === undefined) return null;
  const labels = mergeLabels(configuration.labels);
  const move = async (operation: () => ReturnType<ProgramKitWizardController["select"]>) => {
    const result = await operation();
    if (result.moved) configuration.onStepChange?.(result.snapshot.currentStepId, result.snapshot);
  };
  const finish = async () => {
    const result = await controller.finish();
    if (result.moved) await configuration.onFinish?.(contextRef.current.core?.data, result.snapshot);
  };

  return (
    <section
      aria-busy={snapshot.busy}
      className="pk-form-wizard"
      data-complete={snapshot.completed || undefined}
      data-wizard-id={definition.id}
    >
      <ProgramKitWizardNavigation
        definition={definition}
        labels={configuration.labels}
        onSelect={stepId => { void move(() => controller.select(stepId)); }}
        renderIcon={configuration.renderIcon}
        snapshot={snapshot}
        translateStep={step => step.translationKey === undefined
          ? step.label
          : programKitRuntime?.translate(step.translationKey, step.label)
            ?? context.i18n?.translate?.(step.translationKey, step.label)
            ?? step.label}
      />
      <div
        aria-labelledby={stepButtonId(definition.id, active.id)}
        className="pk-form-wizard__panel"
        id={panelId(definition.id, active.id)}
      >
        <JsonFormsDispatch
          enabled={props.enabled}
          path={props.path}
          schema={props.schema}
          uischema={active.uiSchema as unknown as UISchemaElement}
          {...(props.cells === undefined ? {} : { cells: props.cells })}
          {...(props.renderers === undefined ? {} : { renderers: props.renderers })}
        />
      </div>
      <div className="pk-form-wizard__actions">
        <button
          className="pk-form-wizard__back"
          disabled={snapshot.busy || active.index === 0}
          onClick={() => {
            const result = controller.back();
            if (result.moved) configuration.onStepChange?.(result.snapshot.currentStepId, result.snapshot);
          }}
          type="button"
        >
          {labels.back}
        </button>
        {active.optional && (
          <button
            className="pk-form-wizard__skip"
            disabled={snapshot.busy || active.index === snapshot.steps.length - 1}
            onClick={() => {
              const result = controller.skip();
              if (result.moved) configuration.onStepChange?.(result.snapshot.currentStepId, result.snapshot);
            }}
            type="button"
          >
            {labels.skip}
          </button>
        )}
        {active.index < snapshot.steps.length - 1 ? (
          <button
            className="pk-form-wizard__next"
            disabled={snapshot.busy}
            onClick={() => { void move(() => controller.next()); }}
            type="button"
          >
            {labels.next}
          </button>
        ) : (
          <button
            className="pk-form-wizard__finish"
            disabled={snapshot.busy}
            onClick={() => { void finish(); }}
            type="button"
          >
            {labels.finish}
          </button>
        )}
      </div>
    </section>
  );
}

export const programKitWizardTester: RankedTester = rankWith(
  1000,
  and(uiTypeIs("Categorization"), optionIs("variant", "program-kit-wizard"))
);

export const ProgramKitWizardRenderer = withJsonFormsLayoutProps(ProgramKitWizardRendererComponent);

export const programKitWizardRendererEntry: JsonFormsRendererRegistryEntry = Object.freeze({
  tester: programKitWizardTester,
  renderer: ProgramKitWizardRenderer
});

function stepIsVisible(step: WizardStepDefinition, context: ReturnType<typeof useJsonForms>): boolean {
  const core = context.core;
  if (core?.ajv === undefined) return true;
  return isVisible(
    step.uiSchema as unknown as UISchemaElement,
    core.data,
    "",
    core.ajv,
    context.config
  );
}

function validationIssuesForStep(
  step: WizardStepDefinition | undefined,
  errors: readonly JsonFormsCompatibleValidationError[]
): readonly WizardValidationIssue[] {
  if (step === undefined) return [];
  const scopes = collectScopes(step.uiSchema);
  return errors
    .map(error => ({ error, path: effectiveErrorPath(error) }))
    .filter(candidate => scopes.some(scope => pathContains(scope, candidate.path)))
    .map(({ error, path }) => ({
      stepId: step.id,
      path,
      message: error.message ?? error.keyword,
      severity: "error" as const
    }));
}

function collectScopes(root: JsonObject): readonly string[] {
  const scopes: string[] = [];
  const visit = (value: unknown): void => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (!isRecord(value)) return;
    if (typeof value.scope === "string") scopes.push(schemaScopeToInstancePath(value.scope));
    Object.values(value).forEach(visit);
  };
  visit(root);
  return scopes;
}

function schemaScopeToInstancePath(scope: string): string {
  if (!scope.startsWith("#/properties/")) return scope === "#" ? "" : scope;
  const tokens = scope.slice(2).split("/");
  const values: string[] = [];
  for (let index = 0; index < tokens.length; index += 2) {
    if (tokens[index] !== "properties" || tokens[index + 1] === undefined) return scope;
    values.push(tokens[index + 1] ?? "");
  }
  return "/" + values.join("/");
}

function effectiveErrorPath(error: JsonFormsCompatibleValidationError): string {
  if (error.keyword !== "required" || !isRecord(error.params) || typeof error.params.missingProperty !== "string") {
    return error.instancePath;
  }
  const separator = error.instancePath.endsWith("/") || error.instancePath.length === 0 ? "" : "/";
  return `${error.instancePath}${separator}/${escapePointer(error.params.missingProperty)}`.replace("//", "/");
}

function pathContains(scope: string, errorPath: string): boolean {
  return errorPath === scope || errorPath.startsWith(`${scope}/`) || scope.startsWith(`${errorPath}/`);
}

function escapePointer(value: string): string {
  return value.replaceAll("~", "~0").replaceAll("/", "~1");
}

function trustedWizardConfiguration(value: unknown): ProgramKitWizardReactConfig {
  if (!isRecord(value) || !isRecord(value.programKitWizard)) return {};
  return value.programKitWizard as ProgramKitWizardReactConfig;
}

function trustedActionConfiguration(value: unknown): ProgramKitActionReactConfig {
  if (!isRecord(value) || !isRecord(value.programKitActions)) return {};
  return value.programKitActions as ProgramKitActionReactConfig;
}

function mergeLabels(overrides: ProgramKitWizardReactConfig["labels"]): ProgramKitWizardLabels {
  return {
    ...defaultLabels,
    ...overrides,
    status: { ...defaultLabels.status, ...overrides?.status }
  };
}

function safeDomId(value: string): string {
  return value.replaceAll(/[^a-zA-Z0-9_-]/g, "-");
}

function stepButtonId(wizardId: string, stepId: string): string {
  return `pk-wizard-${safeDomId(wizardId)}-${safeDomId(stepId)}-step`;
}

function navigateByKeyboard(
  event: KeyboardEvent<HTMLButtonElement>,
  stepId: string,
  snapshot: WizardSnapshot,
  wizardId: string,
  onSelect: (stepId: string) => void
): void {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
  const selectable = snapshot.steps.filter(step => step.selectable);
  if (selectable.length === 0) return;
  const currentIndex = Math.max(0, selectable.findIndex(step => step.id === stepId));
  const rtl = event.currentTarget.ownerDocument.documentElement.dir.toLowerCase() === "rtl";
  const forward = event.key === "ArrowRight" ? !rtl : rtl;
  const target = event.key === "Home"
    ? selectable[0]
    : event.key === "End"
      ? selectable.at(-1)
      : selectable[(currentIndex + (forward ? 1 : -1) + selectable.length) % selectable.length];
  if (target === undefined) return;
  event.preventDefault();
  event.currentTarget.ownerDocument.getElementById(stepButtonId(wizardId, target.id))?.focus();
  onSelect(target.id);
}

function panelId(wizardId: string, stepId: string): string {
  return `pk-wizard-${safeDomId(wizardId)}-${safeDomId(stepId)}-panel`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export type { WizardSnapshot };
