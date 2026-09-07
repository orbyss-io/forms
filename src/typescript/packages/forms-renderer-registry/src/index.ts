import type {
  FormActionRequirement,
  FormRendererRequirement,
  JsonObject,
  JsonValue
} from "@orbyss-io/forms-contracts";

export interface RendererRegistration<TRenderer = unknown> {
  readonly componentId: string;
  readonly version: string;
  readonly rank: (uiSchema: JsonObject, dataSchema: JsonObject) => number;
  readonly renderer: TRenderer;
}

export class RendererRegistry<TRenderer = unknown> {
  readonly #registrations: readonly RendererRegistration<TRenderer>[];

  public constructor(registrations: readonly RendererRegistration<TRenderer>[]) {
    const identities = new Set<string>();
    for (const registration of registrations) {
      const identity = `${registration.componentId}@${registration.version}`;
      if (identities.has(identity)) {
        throw new Error(`Duplicate renderer registration '${identity}'.`);
      }
      identities.add(identity);
    }
    this.#registrations = [...registrations];
  }

  public require(requirements: readonly FormRendererRequirement[]): void {
    for (const requirement of requirements) {
      const compatible = this.#registrations.some(
        registration => registration.componentId === requirement.componentId
          && satisfiesMajorRange(registration.version, requirement.versionRange)
      );
      if (!compatible) {
        throw new Error(`Required renderer '${requirement.componentId}' ${requirement.versionRange} is not installed.`);
      }
    }
  }

  public resolve(uiSchema: JsonObject, dataSchema: JsonObject): TRenderer | undefined {
    return this.#registrations
      .map(registration => ({ registration, rank: registration.rank(uiSchema, dataSchema) }))
      .filter(candidate => Number.isFinite(candidate.rank) && candidate.rank >= 0)
      .sort((left, right) => right.rank - left.rank)[0]?.registration.renderer;
  }
}

export interface FormActionContext {
  readonly formId: string;
  readonly releaseId: string;
  readonly signal: AbortSignal;
}

export type FormActionHandler<TResult = JsonValue> = (
  payload: JsonValue,
  context: FormActionContext
) => Promise<TResult>;

export class FormActionRegistry {
  readonly #handlers: ReadonlyMap<string, FormActionHandler>;

  public constructor(handlers: Readonly<Record<string, FormActionHandler>>) {
    this.#handlers = new Map(Object.entries(handlers));
  }

  public require(requirements: readonly FormActionRequirement[]): void {
    for (const requirement of requirements) {
      if (!this.#handlers.has(requirement.handlerId)) {
        throw new Error(`Required action handler '${requirement.handlerId}' is not registered.`);
      }
    }
  }

  public async invoke(
    requirement: FormActionRequirement,
    payload: JsonValue,
    context: FormActionContext
  ): Promise<JsonValue> {
    const handler = this.#handlers.get(requirement.handlerId);
    if (handler === undefined) {
      throw new Error(`Action handler '${requirement.handlerId}' is not registered.`);
    }
    return handler(payload, context);
  }
}

function satisfiesMajorRange(version: string, range: string): boolean {
  const major = Number.parseInt(version.split(".")[0] ?? "", 10);
  const match = /^\[(\d+)\.0\.0,(\d+)\.0\.0\)$/.exec(range);
  return match !== null
    && Number.isInteger(major)
    && major >= Number.parseInt(match[1] ?? "", 10)
    && major < Number.parseInt(match[2] ?? "", 10);
}
