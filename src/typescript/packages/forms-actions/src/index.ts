import type {
  FormActionRequirement,
  JsonObject,
  JsonValue,
  ProgramKitValidator,
  RuntimeValidationIssue
} from "@orbyss-io/program-kit-forms-contracts";

export type ActionAvailability = "enabled" | "disabled" | "hidden";
export type ActionExecutionStatus = "idle" | "running" | "succeeded" | "failed" | "blocked" | "cancelled";

export interface ProgramKitActionDefinition extends FormActionRequirement {
  readonly position: number;
}

export interface ProgramKitActionBarDefinition {
  readonly id: string;
  readonly actions: readonly ProgramKitActionDefinition[];
}

export interface ActionFailure {
  readonly code: string;
  readonly message: string;
  readonly retryable: boolean;
}

export interface ProgramKitActionSnapshot extends ProgramKitActionDefinition {
  readonly availability: ActionAvailability;
  readonly status: ActionExecutionStatus;
  readonly failure?: ActionFailure;
}

export interface ProgramKitActionBarSnapshot {
  readonly runningActionId?: string;
  readonly actions: readonly ProgramKitActionSnapshot[];
}

export interface ProgramKitActionExecutionContext {
  readonly data: JsonValue;
  readonly signal?: AbortSignal;
}

export interface ProgramKitActionControllerOptions {
  readonly validate: ProgramKitValidator;
  readonly dispatch: (actionId: string, payload: JsonValue, signal: AbortSignal) => Promise<JsonValue>;
  readonly availability?: (action: ProgramKitActionDefinition) => ActionAvailability;
  readonly onChange?: (snapshot: ProgramKitActionBarSnapshot) => void;
}

export interface ProgramKitActionResult {
  readonly invoked: boolean;
  readonly reason?: "busy" | "disabled" | "hidden" | "validation" | "cancelled" | "failed";
  readonly value?: JsonValue;
  readonly issues?: readonly RuntimeValidationIssue[];
  readonly snapshot: ProgramKitActionBarSnapshot;
}

/** A deliberately public-safe failure; unexpected exceptions are replaced with a generic message. */
export class ProgramKitActionError extends Error {
  public constructor(
    public readonly code: string,
    message: string,
    public readonly retryable = false
  ) {
    super(message);
    this.name = "ProgramKitActionError";
  }
}

export class ProgramKitActionController {
  readonly #definition: ProgramKitActionBarDefinition;
  readonly #options: ProgramKitActionControllerOptions;
  readonly #states = new Map<string, { status: ActionExecutionStatus; failure?: ActionFailure }>();
  #runningActionId: string | undefined;
  #abort: AbortController | undefined;

  public constructor(definition: ProgramKitActionBarDefinition, options: ProgramKitActionControllerOptions) {
    this.#definition = definition;
    this.#options = options;
    for (const action of definition.actions) this.#states.set(action.actionId, { status: "idle" });
  }

  public snapshot(): ProgramKitActionBarSnapshot {
    return Object.freeze({
      ...(this.#runningActionId === undefined ? {} : { runningActionId: this.#runningActionId }),
      actions: Object.freeze(this.#definition.actions.map(action => {
        const state = this.#states.get(action.actionId) ?? { status: "idle" as const };
        return Object.freeze({
          ...action,
          availability: this.#availability(action),
          status: state.status,
          ...(state.failure === undefined ? {} : { failure: Object.freeze({ ...state.failure }) })
        });
      }))
    });
  }

  public async invoke(
    actionId: string,
    payload: JsonValue,
    context: ProgramKitActionExecutionContext
  ): Promise<ProgramKitActionResult> {
    const action = this.#action(actionId);
    if (this.#runningActionId !== undefined) return this.#result(false, "busy");
    const availability = this.#availability(action);
    if (availability === "hidden") return this.#result(false, "hidden");
    if (availability === "disabled") return this.#result(false, "disabled");
    if (action.requiresValidForm) {
      const issues = Object.freeze([...this.#options.validate(context.data)]);
      if (issues.length > 0) {
        this.#states.set(actionId, {
          status: "blocked",
          failure: { code: "PKA001", message: "Resolve the form validation errors before continuing.", retryable: true }
        });
        this.#notify();
        return { invoked: false, reason: "validation", issues, snapshot: this.snapshot() };
      }
    }

    const abort = new AbortController();
    const cancelFromCaller = () => abort.abort(context.signal?.reason);
    if (context.signal?.aborted) abort.abort(context.signal.reason);
    else context.signal?.addEventListener("abort", cancelFromCaller, { once: true });
    this.#abort = abort;
    this.#runningActionId = actionId;
    this.#states.set(actionId, { status: "running" });
    this.#notify();
    let result: Omit<ProgramKitActionResult, "snapshot">;
    try {
      abort.signal.throwIfAborted();
      const value = await this.#options.dispatch(actionId, payload, abort.signal);
      abort.signal.throwIfAborted();
      this.#states.set(actionId, { status: "succeeded" });
      result = { invoked: true, value };
    } catch (error) {
      if (abort.signal.aborted || isAbortError(error)) {
        this.#states.set(actionId, { status: "cancelled" });
        result = { invoked: false, reason: "cancelled" };
      } else {
        const failure = error instanceof ProgramKitActionError
          ? { code: error.code, message: error.message, retryable: error.retryable }
          : { code: "PKA999", message: "The action could not be completed.", retryable: false };
        this.#states.set(actionId, { status: "failed", failure });
        result = { invoked: false, reason: "failed" };
      }
    } finally {
      context.signal?.removeEventListener("abort", cancelFromCaller);
      this.#runningActionId = undefined;
      this.#abort = undefined;
      this.#notify();
    }
    return { ...result, snapshot: this.snapshot() };
  }

  public cancel(): boolean {
    if (this.#abort === undefined) return false;
    this.#abort.abort();
    return true;
  }

  public reset(actionId: string): ProgramKitActionBarSnapshot {
    if (this.#runningActionId === actionId) throw new Error("A running action cannot be reset.");
    this.#action(actionId);
    this.#states.set(actionId, { status: "idle" });
    this.#notify();
    return this.snapshot();
  }

  #availability(action: ProgramKitActionDefinition): ActionAvailability {
    try {
      return this.#options.availability?.(action) ?? "enabled";
    } catch {
      return "disabled";
    }
  }

  #action(actionId: string): ProgramKitActionDefinition {
    const action = this.#definition.actions.find(candidate => candidate.actionId === actionId);
    if (action === undefined) throw new Error(`Action '${actionId}' is not declared by this action bar.`);
    return action;
  }

  #notify(): void {
    this.#options.onChange?.(this.snapshot());
  }

  #result(invoked: boolean, reason: NonNullable<ProgramKitActionResult["reason"]>): ProgramKitActionResult {
    return { invoked, reason, snapshot: this.snapshot() };
  }
}

export function parseProgramKitActionBar(
  uiSchema: JsonObject,
  requirements: readonly FormActionRequirement[]
): ProgramKitActionBarDefinition {
  if (uiSchema.type !== "ProgramKit.ActionBar") throw new Error("The UI element is not a Program Kit action bar.");
  const options = requireObject(uiSchema.options, "Action-bar options");
  if (!Array.isArray(options.actions) || options.actions.length === 0) {
    throw new Error("A Program Kit action bar requires a non-empty actions array.");
  }
  const byId = new Map(requirements.map(requirement => [requirement.actionId, requirement]));
  const seen = new Set<string>();
  const actions = options.actions.map((value, position) => {
    if (typeof value !== "string" || value.length === 0) throw new Error(`Action reference ${position + 1} must be a non-empty string.`);
    if (seen.has(value)) throw new Error(`Action '${value}' is repeated by the action bar.`);
    seen.add(value);
    const requirement = byId.get(value);
    if (requirement === undefined) throw new Error(`Action '${value}' is absent from the immutable release manifest.`);
    return Object.freeze({ ...requirement, position });
  });
  return Object.freeze({
    id: typeof uiSchema.id === "string" && uiSchema.id.length > 0 ? uiSchema.id : "actions",
    actions: Object.freeze(actions)
  });
}

function requireObject(value: JsonValue | undefined, label: string): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) throw new Error(`${label} must be an object.`);
  return value;
}

function isAbortError(value: unknown): boolean {
  return typeof value === "object" && value !== null && "name" in value && value.name === "AbortError";
}
