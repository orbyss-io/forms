import type { JsonObject, JsonValue, ProgramKitTranslator } from "@orbyss/program-kit-forms-contracts";

export type WizardNavigationPolicy = "linear" | "visited" | "nonLinear";
export type WizardNavigationPlacement = "top" | "side" | "adaptive";
export type WizardProgressStyle = "line" | "progress" | "segmented" | "none";
export type WizardStepStatus = "current" | "completed" | "visited" | "upcoming" | "warning" | "error" | "skipped" | "disabled";

export interface WizardIconReference {
  readonly name: string;
  readonly bundle?: string;
}

export interface WizardStepDefinition {
  readonly id: string;
  readonly label: string;
  readonly translationKey?: string;
  readonly icon?: WizardIconReference;
  readonly optional: boolean;
  readonly disabled: boolean;
  readonly uiSchema: JsonObject;
}

export interface ProgramKitWizardDefinition {
  readonly id: string;
  readonly navigationPolicy: WizardNavigationPolicy;
  readonly navigationPlacement: WizardNavigationPlacement;
  readonly progressStyle: WizardProgressStyle;
  readonly validateBeforeAdvance: boolean;
  readonly saveProgress: boolean;
  readonly deepLink: boolean;
  readonly steps: readonly WizardStepDefinition[];
}

export interface WizardValidationIssue {
  readonly stepId: string;
  readonly path: string;
  readonly message: string;
  readonly severity: "warning" | "error";
}

export interface WizardStepSnapshot extends WizardStepDefinition {
  readonly index: number;
  readonly status: WizardStepStatus;
  readonly selectable: boolean;
  readonly issues: readonly WizardValidationIssue[];
}

export interface WizardSnapshot {
  readonly currentStepId: string;
  readonly busy: boolean;
  readonly completed: boolean;
  readonly progress: number;
  readonly steps: readonly WizardStepSnapshot[];
}

export interface WizardControllerOptions {
  readonly initialStepId?: string;
  readonly visibleStepIds?: readonly string[];
  readonly validateStep?: (stepId: string, signal: AbortSignal) => Promise<readonly WizardValidationIssue[]>;
  readonly onChange?: (snapshot: WizardSnapshot) => void;
}

export interface WizardMoveResult {
  readonly moved: boolean;
  readonly reason?: "busy" | "disabled" | "hidden" | "policy" | "validation" | "boundary";
  readonly snapshot: WizardSnapshot;
}

export class ProgramKitWizardController {
  readonly #definition: ProgramKitWizardDefinition;
  readonly #validateStep?: WizardControllerOptions["validateStep"];
  readonly #onChange?: WizardControllerOptions["onChange"];
  readonly #visited = new Set<string>();
  readonly #completed = new Set<string>();
  readonly #skipped = new Set<string>();
  readonly #issues = new Map<string, readonly WizardValidationIssue[]>();
  #visible: Set<string>;
  #currentStepId: string;
  #busy = false;
  #finished = false;

  public constructor(definition: ProgramKitWizardDefinition, options: WizardControllerOptions = {}) {
    if (definition.steps.length === 0) throw new Error("A Program Kit wizard requires at least one step.");
    this.#definition = definition;
    this.#validateStep = options.validateStep;
    this.#onChange = options.onChange;
    this.#visible = validateVisibleSteps(definition, options.visibleStepIds ?? definition.steps.map(step => step.id));
    const initial = options.initialStepId ?? this.#firstEnabledVisibleStep()?.id;
    if (initial === undefined || !this.#visible.has(initial)) throw new Error("The initial wizard step must be visible.");
    const initialStep = this.#step(initial);
    if (initialStep.disabled) throw new Error("The initial wizard step must be enabled.");
    this.#currentStepId = initial;
    this.#visited.add(initial);
  }

  public snapshot(): WizardSnapshot {
    const steps = this.#visibleSteps();
    const actionable = steps.filter(step => !step.disabled);
    const progressed = actionable.filter(step => this.#completed.has(step.id) || this.#skipped.has(step.id)).length;
    return Object.freeze({
      currentStepId: this.#currentStepId,
      busy: this.#busy,
      completed: this.#finished,
      progress: actionable.length === 0 ? 0 : (this.#finished ? 1 : progressed / actionable.length),
      steps: Object.freeze(steps.map((step, index) => Object.freeze({
        ...step,
        index,
        status: this.#status(step),
        selectable: this.#canSelect(step),
        issues: Object.freeze([...(this.#issues.get(step.id) ?? [])])
      })))
    });
  }

  public async select(stepId: string, signal: AbortSignal = new AbortController().signal): Promise<WizardMoveResult> {
    if (this.#busy) return this.#result(false, "busy");
    if (!this.#visible.has(stepId)) return this.#result(false, "hidden");
    const target = this.#step(stepId);
    if (target.disabled) return this.#result(false, "disabled");
    if (!this.#canSelect(target)) return this.#result(false, "policy");
    if (target.id === this.#currentStepId) return this.#result(false, "boundary");
    if (this.#indexOf(target.id) > this.#indexOf(this.#currentStepId) && !await this.#completeCurrent(signal)) {
      return this.#result(false, "validation");
    }
    this.#activate(target.id);
    return this.#result(true);
  }

  public async next(signal: AbortSignal = new AbortController().signal): Promise<WizardMoveResult> {
    if (this.#busy) return this.#result(false, "busy");
    const currentIndex = this.#indexOf(this.#currentStepId);
    const target = this.#visibleSteps().find((step, index) => index > currentIndex && !step.disabled);
    if (target === undefined) return this.#result(false, "boundary");
    if (!await this.#completeCurrent(signal)) return this.#result(false, "validation");
    this.#activate(target.id);
    return this.#result(true);
  }

  public back(): WizardMoveResult {
    if (this.#busy) return this.#result(false, "busy");
    const currentIndex = this.#indexOf(this.#currentStepId);
    const target = this.#visibleSteps().slice(0, currentIndex).reverse().find(step => !step.disabled);
    if (target === undefined) return this.#result(false, "boundary");
    this.#activate(target.id);
    return this.#result(true);
  }

  public skip(): WizardMoveResult {
    if (this.#busy) return this.#result(false, "busy");
    const current = this.#step(this.#currentStepId);
    if (!current.optional) return this.#result(false, "policy");
    const currentIndex = this.#indexOf(current.id);
    const target = this.#visibleSteps().find((step, index) => index > currentIndex && !step.disabled);
    if (target === undefined) return this.#result(false, "boundary");
    this.#issues.delete(current.id);
    this.#skipped.add(current.id);
    this.#completed.delete(current.id);
    this.#activate(target.id);
    return this.#result(true);
  }

  public async finish(signal: AbortSignal = new AbortController().signal): Promise<WizardMoveResult> {
    if (this.#busy) return this.#result(false, "busy");
    const actionable = this.#visibleSteps().filter(step => !step.disabled);
    if (actionable.at(-1)?.id !== this.#currentStepId) return this.#result(false, "boundary");
    if (!await this.#completeCurrent(signal)) return this.#result(false, "validation");
    this.#finished = true;
    this.#notify();
    return this.#result(true);
  }

  public updateVisibleSteps(stepIds: readonly string[]): WizardSnapshot {
    const previous = this.#visibleSteps();
    const previousIndex = previous.findIndex(step => step.id === this.#currentStepId);
    this.#visible = validateVisibleSteps(this.#definition, stepIds);
    if (!this.#visible.has(this.#currentStepId)) {
      const ordered = this.#visibleSteps();
      const replacement = ordered.filter(step => !step.disabled).at(Math.min(previousIndex, ordered.length - 1))
        ?? [...ordered].reverse().find(step => !step.disabled);
      if (replacement === undefined) throw new Error("A wizard must retain at least one enabled visible step.");
      this.#activate(replacement.id);
    } else {
      this.#notify();
    }
    return this.snapshot();
  }

  async #completeCurrent(signal: AbortSignal): Promise<boolean> {
    const current = this.#currentStepId;
    if (!this.#definition.validateBeforeAdvance || this.#validateStep === undefined) {
      this.#completed.add(current);
      this.#skipped.delete(current);
      return true;
    }
    this.#busy = true;
    this.#notify();
    try {
      signal.throwIfAborted();
      const issues = Object.freeze([...(await this.#validateStep(current, signal))]);
      signal.throwIfAborted();
      this.#issues.set(current, issues);
      if (issues.some(issue => issue.severity === "error")) return false;
      this.#completed.add(current);
      this.#skipped.delete(current);
      return true;
    } finally {
      this.#busy = false;
      this.#notify();
    }
  }

  #activate(stepId: string): void {
    this.#currentStepId = stepId;
    this.#visited.add(stepId);
    this.#finished = false;
    this.#notify();
  }

  #status(step: WizardStepDefinition): WizardStepStatus {
    if (step.disabled) return "disabled";
    const issues = this.#issues.get(step.id) ?? [];
    if (issues.some(issue => issue.severity === "error")) return "error";
    if (issues.some(issue => issue.severity === "warning")) return "warning";
    if (step.id === this.#currentStepId && !this.#finished) return "current";
    if (this.#skipped.has(step.id)) return "skipped";
    if (this.#completed.has(step.id)) return "completed";
    if (this.#visited.has(step.id)) return "visited";
    return "upcoming";
  }

  #canSelect(step: WizardStepDefinition): boolean {
    if (this.#busy || step.disabled || !this.#visible.has(step.id)) return false;
    if (step.id === this.#currentStepId || this.#definition.navigationPolicy === "nonLinear") return true;
    if (this.#definition.navigationPolicy === "visited") return this.#visited.has(step.id);
    return this.#visited.has(step.id) && this.#indexOf(step.id) < this.#indexOf(this.#currentStepId);
  }

  #firstEnabledVisibleStep(): WizardStepDefinition | undefined {
    return this.#visibleSteps().find(step => !step.disabled);
  }

  #visibleSteps(): WizardStepDefinition[] {
    return this.#definition.steps.filter(step => this.#visible.has(step.id));
  }

  #indexOf(stepId: string): number {
    return this.#visibleSteps().findIndex(step => step.id === stepId);
  }

  #step(stepId: string): WizardStepDefinition {
    const step = this.#definition.steps.find(candidate => candidate.id === stepId);
    if (step === undefined) throw new Error(`Unknown wizard step '${stepId}'.`);
    return step;
  }

  #notify(): void {
    this.#onChange?.(this.snapshot());
  }

  #result(moved: boolean, reason?: WizardMoveResult["reason"]): WizardMoveResult {
    return reason === undefined ? { moved, snapshot: this.snapshot() } : { moved, reason, snapshot: this.snapshot() };
  }
}

export function parseProgramKitWizard(
  uiSchema: JsonObject,
  translate: (key: string, fallback: string) => string = (_key, fallback) => fallback
): ProgramKitWizardDefinition {
  if (uiSchema.type !== "Categorization") throw new Error("The Program Kit wizard root must be a JSON Forms Categorization.");
  const options = objectProperty(uiSchema, "options");
  if (options.variant !== "program-kit-wizard") throw new Error("The Categorization does not select the Program Kit wizard variant.");
  const elements = arrayProperty(uiSchema, "elements");
  const identities = new Set<string>();
  const steps = elements.map((value, index) => {
    const step = requireObject(value, `Wizard step ${index + 1}`);
    if (step.type !== "Category") throw new Error(`Wizard element ${index + 1} must be a JSON Forms Category.`);
    const id = requiredString(step, "id", `Wizard step ${index + 1}`);
    if (identities.has(id)) throw new Error(`Duplicate wizard step '${id}'.`);
    identities.add(id);
    const fallback = optionalString(step, "label") ?? id;
    const translationKey = optionalString(step, "i18n");
    const stepOptions = optionalObject(step, "options");
    const presentation = stepOptions === undefined ? undefined : optionalObject(stepOptions, "presentation");
    const iconValue = stepOptions === undefined ? undefined : optionalObject(stepOptions, "icon");
    const iconName = iconValue === undefined ? undefined : optionalString(iconValue, "name");
    const iconBundle = iconValue === undefined ? undefined : optionalString(iconValue, "bundle");
    return Object.freeze({
      id,
      label: translationKey === undefined ? fallback : translate(translationKey, fallback),
      ...(translationKey === undefined ? {} : { translationKey }),
      ...(iconName === undefined ? {} : { icon: Object.freeze({
        name: iconName,
        ...(iconBundle === undefined ? {} : { bundle: iconBundle })
      }) }),
      optional: presentation?.optional === "true",
      disabled: presentation?.disabled === "true",
      uiSchema: step
    });
  });
  if (steps.length === 0) throw new Error("A Program Kit wizard requires at least one Category.");
  return Object.freeze({
    id: optionalString(uiSchema, "id") ?? "wizard",
    navigationPolicy: enumOption(options, "navigationPolicy", ["linear", "visited", "nonLinear"], "linear"),
    navigationPlacement: enumOption(options, "navigationPlacement", ["top", "side", "adaptive"], "adaptive"),
    progressStyle: enumOption(options, "progressStyle", ["line", "progress", "segmented", "none"], "progress"),
    validateBeforeAdvance: booleanOption(options, "validateBeforeAdvance", true),
    saveProgress: booleanOption(options, "saveProgress", false),
    deepLink: booleanOption(options, "deepLink", false),
    steps: Object.freeze(steps)
  });
}

function validateVisibleSteps(definition: ProgramKitWizardDefinition, values: readonly string[]): Set<string> {
  const known = new Set(definition.steps.map(step => step.id));
  const visible = new Set<string>();
  for (const value of values) {
    if (!known.has(value)) throw new Error(`Unknown visible wizard step '${value}'.`);
    if (visible.has(value)) throw new Error(`Duplicate visible wizard step '${value}'.`);
    visible.add(value);
  }
  if (!definition.steps.some(step => visible.has(step.id) && !step.disabled)) {
    throw new Error("A wizard requires at least one enabled visible step.");
  }
  return visible;
}

function enumOption<T extends string>(object: JsonObject, property: string, allowed: readonly T[], fallback: T): T {
  const value = object[property];
  if (value === undefined) return fallback;
  if (typeof value !== "string" || !allowed.includes(value as T)) throw new Error(`Wizard option '${property}' is invalid.`);
  return value as T;
}

function booleanOption(object: JsonObject, property: string, fallback: boolean): boolean {
  const value = object[property];
  if (value === undefined) return fallback;
  if (typeof value !== "boolean") throw new Error(`Wizard option '${property}' must be boolean.`);
  return value;
}

function objectProperty(object: JsonObject, property: string): JsonObject {
  const value = object[property];
  if (!isObject(value)) throw new Error(`Wizard property '${property}' must be an object.`);
  return value;
}

function optionalObject(object: JsonObject, property: string): JsonObject | undefined {
  const value = object[property];
  if (value === undefined) return undefined;
  if (!isObject(value)) throw new Error(`Wizard property '${property}' must be an object.`);
  return value;
}

function arrayProperty(object: JsonObject, property: string): readonly JsonValue[] {
  const value = object[property];
  if (!Array.isArray(value)) throw new Error(`Wizard property '${property}' must be an array.`);
  return value;
}

function requiredString(object: JsonObject, property: string, label: string): string {
  const value = optionalString(object, property);
  if (value === undefined || value.trim().length === 0) throw new Error(`${label} requires a non-empty '${property}'.`);
  return value;
}

function optionalString(object: JsonObject, property: string): string | undefined {
  const value = object[property];
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "string") throw new Error(`Wizard property '${property}' must be a string.`);
  return value;
}

function requireObject(value: JsonValue, label: string): JsonObject {
  if (!isObject(value)) throw new Error(`${label} must be an object.`);
  return value;
}

function isObject(value: JsonValue | undefined): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
