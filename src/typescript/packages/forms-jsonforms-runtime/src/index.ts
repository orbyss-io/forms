import {
  defaultRuntimeLimits,
  type FormActionRequirement,
  type FormRelease,
  type JsonObject,
  type JsonValue,
  type ProgramKitTranslator,
  type ProgramKitValidator,
  type RuntimeValidationIssue,
  type RuntimeLimits
} from "@orbyss/program-kit-forms-contracts";
import {
  FormActionRegistry,
  RendererRegistry,
  type FormActionContext
} from "@orbyss/program-kit-forms-renderer-registry";

export interface PreparedJsonFormsRuntime<TRenderer> {
  readonly schema: JsonObject;
  readonly uiSchema: JsonObject;
  readonly renderers: RendererRegistry<TRenderer>;
  readonly validate: ProgramKitValidator;
  readonly translate: ProgramKitTranslator;
  readonly actions: readonly FormActionRequirement[];
  readonly dispatchAction: (
    actionId: string,
    payload: JsonValue,
    context: Omit<FormActionContext, "formId" | "releaseId">
  ) => Promise<JsonValue>;
}

export async function prepareJsonFormsRuntime<TRenderer>(
  release: FormRelease,
  renderers: RendererRegistry<TRenderer>,
  actions: FormActionRegistry,
  validate: ProgramKitValidator,
  translate: ProgramKitTranslator,
  limits: RuntimeLimits = defaultRuntimeLimits
): Promise<PreparedJsonFormsRuntime<TRenderer>> {
  if (release.retired) {
    throw new Error("A retired form release cannot start a new runtime journey.");
  }
  if (release.candidate.diagnostics.some(diagnostic => diagnostic.severity === "error" || diagnostic.severity === 2)) {
    throw new Error("A form release containing blocking diagnostics cannot be rendered.");
  }
  await verifyArtifact(release.candidate.dataSchema.content, release.candidate.dataSchema.sha256, limits);
  await verifyArtifact(release.candidate.uiSchema.content, release.candidate.uiSchema.sha256, limits);
  const schema = parseBoundedObject(release.candidate.dataSchema.content, limits, "data schema");
  const uiSchema = parseBoundedObject(release.candidate.uiSchema.content, limits, "UI schema");
  rejectExternalReferences(schema);
  validateUiSchema(uiSchema, release.candidate.renderers, limits);
  renderers.require(release.candidate.renderers);
  actions.require(release.candidate.actions);
  const actionById = new Map(release.candidate.actions.map(action => [action.actionId, action]));
  return {
    schema,
    uiSchema,
    renderers,
    validate,
    translate,
    actions: Object.freeze([...release.candidate.actions]),
    dispatchAction: async (actionId, payload, context) => {
      const requirement = actionById.get(actionId);
      if (requirement === undefined) {
        throw new Error(`Action '${actionId}' is not declared by this release.`);
      }
      return actions.invoke(requirement, payload, {
        ...context,
        formId: release.candidate.formId.value,
        releaseId: release.id.value
      });
    }
  };
}

export function createJsonFormsTranslator(
  translations: Readonly<Record<string, string>>
): ProgramKitTranslator {
  const snapshot = Object.freeze({ ...translations });
  return (key, fallback) => snapshot[key] ?? fallback;
}

function parseBoundedObject(content: string, limits: RuntimeLimits, label: string): JsonObject {
  if (new TextEncoder().encode(content).byteLength > limits.maximumArtifactBytes) {
    throw new Error(`The ${label} exceeds the configured byte limit.`);
  }
  const value: unknown = JSON.parse(content);
  if (!isJsonObject(value)) {
    throw new Error(`The ${label} root must be a JSON object.`);
  }
  inspectGraph(value, limits);
  return value;
}

function inspectGraph(root: JsonValue, limits: RuntimeLimits): void {
  let nodes = 0;
  const pending: Array<{ readonly value: JsonValue; readonly depth: number }> = [{ value: root, depth: 1 }];
  while (pending.length > 0) {
    const current = pending.pop();
    if (current === undefined) continue;
    nodes += 1;
    if (nodes > limits.maximumJsonNodes) throw new Error("The form artifact exceeds the configured node limit.");
    if (current.depth > limits.maximumJsonDepth) throw new Error("The form artifact exceeds the configured depth limit.");
    if (Array.isArray(current.value)) {
      for (const value of current.value) pending.push({ value, depth: current.depth + 1 });
    } else if (isJsonObject(current.value)) {
      for (const [key, value] of Object.entries(current.value)) {
        if (key === "__proto__" || key === "prototype" || key === "constructor" || /^on/i.test(key)) {
          throw new Error(`Executable or prototype-sensitive key '${key}' is forbidden.`);
        }
        pending.push({ value, depth: current.depth + 1 });
      }
    }
  }
}

function rejectExternalReferences(root: JsonValue): void {
  walk(root, (key, value) => {
    if (key === "$ref" && typeof value === "string" && !value.startsWith("#")) {
      throw new Error(`External schema reference '${value}' must be bundled before runtime.`);
    }
  });
}

function validateUiSchema(
  root: JsonObject,
  requirements: readonly { readonly componentId: string }[],
  limits: RuntimeLimits
): void {
  const builtIn = new Set(["Control", "Group", "HorizontalLayout", "VerticalLayout", "Categorization", "Category", "Label"]);
  const custom = new Set(requirements.map(requirement => requirement.componentId));
  walk(root, (key, value, owner) => {
    if ((key === "html" || key === "script" || key === "href" || key === "src" || key === "url") && value !== null) {
      throw new Error(`UI Schema property '${key}' is forbidden.`);
    }
    if (key === "type" && typeof value === "string" && owner !== undefined && "id" in owner
      && !builtIn.has(value) && !custom.has(value)) {
      throw new Error(`UI Schema element type '${value}' is not allowlisted by the release manifest.`);
    }
  });
  inspectGraph(root, limits);
}

async function verifyArtifact(content: string, expected: string, limits: RuntimeLimits): Promise<void> {
  if (new TextEncoder().encode(content).byteLength > limits.maximumArtifactBytes) {
    throw new Error("The form artifact exceeds the configured byte limit.");
  }
  const actual = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content))))
    .map(value => value.toString(16).padStart(2, "0"))
    .join("");
  if (actual !== expected.toLowerCase()) throw new Error("The form artifact failed SHA-256 verification.");
}

function walk(
  root: JsonValue,
  visit: (key: string, value: JsonValue, owner?: JsonObject) => void
): void {
  if (Array.isArray(root)) {
    for (const value of root) walk(value, visit);
  } else if (isJsonObject(root)) {
    for (const [key, value] of Object.entries(root)) {
      visit(key, value, root);
      walk(value, visit);
    }
  }
}

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export type { FormActionRequirement };
