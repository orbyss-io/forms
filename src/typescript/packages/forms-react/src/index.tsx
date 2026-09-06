import {
  and,
  isVisible,
  optionIs,
  rankWith,
  uiTypeIs,
  type JsonFormsRendererRegistryEntry,
  type LayoutProps,
  type RankedTester,
  type UISchemaElement
} from "@jsonforms/core";
import {
  JsonFormsDispatch,
  JsonForms,
  useJsonForms,
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

export const programKitReactFormsAdapterVersion = "1.0.0";

interface JsonFormsValidationError {
  readonly instancePath: string;
  readonly keyword: string;
  readonly message?: string;
  readonly params: unknown;
}

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
 * executable code in the browser; rule conditions use only the bounded portable subset below.
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
    () => createPrecompiledValidatorFacade(runtime.schema, runtime.validate),
    [runtime.schema, runtime.validate]
  );
  const rendererEntries = useMemo(
    () => [programKitWizardRendererEntry, programKitActionBarRendererEntry, ...renderers],
    [renderers]
  );
  return (
    <ProgramKitFormsRuntimeContext.Provider value={runtime}>
      <JsonForms
        ajv={ajv}
        data={data}
        i18n={{ translate: (key, fallback) => runtime.translate(key, fallback ?? key) }}
        renderers={rendererEntries}
        schema={runtime.schema}
        uischema={runtime.uiSchema as unknown as UISchemaElement}
        {...(cells === undefined ? {} : { cells: [...cells] })}
        {...(config === undefined ? {} : { config })}
        {...(readonly === undefined ? {} : { readonly })}
        {...(onChange === undefined ? {} : {
          onChange: state => onChange(
            state.data as JsonValue,
            validationErrorsToIssues((state.errors ?? []) as readonly JsonFormsValidationError[])
          )
        })}
      />
    </ProgramKitFormsRuntimeContext.Provider>
  );
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
      (contextRef.current.core?.errors ?? []) as readonly JsonFormsValidationError[]
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
  errors: readonly JsonFormsValidationError[]
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

function effectiveErrorPath(error: JsonFormsValidationError): string {
  if (error.keyword !== "required" || !isRecord(error.params) || typeof error.params.missingProperty !== "string") {
    return error.instancePath;
  }
  const separator = error.instancePath.endsWith("/") || error.instancePath.length === 0 ? "" : "/";
  return `${error.instancePath}${separator}/${escapePointer(error.params.missingProperty)}`.replace("//", "/");
}

function pathContains(scope: string, errorPath: string): boolean {
  return errorPath === scope || errorPath.startsWith(`${scope}/`) || scope.startsWith(`${errorPath}/`);
}

function createPrecompiledValidatorFacade(
  rootSchema: JsonObject,
  validateRoot: ProgramKitValidator
): JsonFormsAjv {
  const rootValidator = createCompatibleValidator(data => validateRoot(data as JsonValue));
  const facade = {
    compile(schema: unknown) {
      if (schema === rootSchema) return rootValidator;
      return createCompatibleValidator(data => evaluatePortableConditionSchema(schema, data)
        ? []
        : [{ path: "", keyword: "condition", message: "The portable condition was not satisfied." }]);
    },
    validate(schema: unknown, data: unknown) {
      return evaluatePortableConditionSchema(schema, data);
    }
  };
  return facade as unknown as JsonFormsAjv;
}

function createCompatibleValidator(
  validate: (data: unknown) => readonly RuntimeValidationIssue[]
): ((data: unknown) => boolean) & { errors: readonly JsonFormsValidationError[] | null } {
  const compatible = ((data: unknown) => {
    const issues = validate(data);
    compatible.errors = issues.length === 0 ? null : issues.map(issue => ({
      instancePath: issue.path,
      keyword: issue.keyword,
      message: issue.message,
      params: issue.property === undefined
        ? {}
        : issue.keyword === "additionalProperties"
          ? { additionalProperty: issue.property }
          : { missingProperty: issue.property }
    }));
    return compatible.errors === null;
  }) as ((data: unknown) => boolean) & { errors: readonly JsonFormsValidationError[] | null };
  compatible.errors = null;
  return compatible;
}

function evaluatePortableConditionSchema(schema: unknown, data: unknown): boolean {
  if (!isRecord(schema)) throw new Error("A JSON Forms condition schema must be an object.");
  const supported = new Set(["const", "enum", "type", "not", "allOf", "anyOf", "oneOf", "required", "properties"]);
  const annotations = new Set(["$id", "$schema", "title", "description"]);
  for (const key of Object.keys(schema)) {
    if (!supported.has(key) && !annotations.has(key)) {
      throw new Error(`Condition keyword '${key}' requires a precompiled validator.`);
    }
  }
  if ("const" in schema && !jsonEqual(data, schema.const)) return false;
  if (Array.isArray(schema.enum) && !schema.enum.some(candidate => jsonEqual(data, candidate))) return false;
  if (typeof schema.type === "string" && !matchesJsonType(data, schema.type)) return false;
  if (schema.not !== undefined && evaluatePortableConditionSchema(schema.not, data)) return false;
  if (Array.isArray(schema.allOf) && !schema.allOf.every(candidate => evaluatePortableConditionSchema(candidate, data))) return false;
  if (Array.isArray(schema.anyOf) && !schema.anyOf.some(candidate => evaluatePortableConditionSchema(candidate, data))) return false;
  if (Array.isArray(schema.oneOf)
    && schema.oneOf.filter(candidate => evaluatePortableConditionSchema(candidate, data)).length !== 1) return false;
  if (Array.isArray(schema.required)) {
    if (!isRecord(data) || !schema.required.every(value => typeof value === "string" && value in data)) return false;
  }
  if (isRecord(schema.properties)) {
    if (!isRecord(data)) return false;
    for (const [property, propertySchema] of Object.entries(schema.properties)) {
      if (property in data && !evaluatePortableConditionSchema(propertySchema, data[property])) return false;
    }
  }
  return true;
}

function matchesJsonType(value: unknown, type: string): boolean {
  return type === "null" ? value === null
    : type === "array" ? Array.isArray(value)
      : type === "object" ? isRecord(value)
        : type === "integer" ? typeof value === "number" && Number.isInteger(value)
          : type === "number" ? typeof value === "number" && Number.isFinite(value)
            : type === "string" ? typeof value === "string"
              : type === "boolean" ? typeof value === "boolean"
                : false;
}

function jsonEqual(left: unknown, right: unknown): boolean {
  if (Object.is(left, right)) return true;
  if (Array.isArray(left) && Array.isArray(right)) {
    return left.length === right.length && left.every((value, index) => jsonEqual(value, right[index]));
  }
  if (isRecord(left) && isRecord(right)) {
    const leftKeys = Object.keys(left).sort();
    const rightKeys = Object.keys(right).sort();
    return leftKeys.length === rightKeys.length
      && leftKeys.every((key, index) => key === rightKeys[index] && jsonEqual(left[key], right[key]));
  }
  return false;
}

function validationErrorsToIssues(errors: readonly JsonFormsValidationError[]): readonly RuntimeValidationIssue[] {
  return errors.map(error => {
    const property = isRecord(error.params)
      ? typeof error.params.missingProperty === "string"
        ? error.params.missingProperty
        : typeof error.params.additionalProperty === "string"
          ? error.params.additionalProperty
          : undefined
      : undefined;
    return {
      path: error.instancePath,
      keyword: error.keyword,
      message: error.message ?? error.keyword,
      ...(property === undefined ? {} : { property })
    };
  });
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
