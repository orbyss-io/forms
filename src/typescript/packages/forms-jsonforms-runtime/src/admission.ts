import { defaultRuntimeLimits, type BoundFormValidator, type FormDeploymentManifest, type FormRelease, type OrbyssValidator, type RuntimeLimits } from "@orbyss-io/forms-contracts";

export interface AdmittedFormRelease {
  readonly release: FormRelease;
  readonly translations: Readonly<Record<string, Readonly<Record<string, string>>>>;
  readonly validate: OrbyssValidator;
}

/**
 * Binds complete release and locale bytes to an app-deployed expectation. The validator's module
 * bytes are checked by the trusted build before static import; callback metadata is not proof of
 * executable provenance. This API never evaluates artifact code or authenticates a publisher.
 */
export async function admitFormRelease(
  releaseJson: string,
  localeJson: Readonly<Record<string, string>>,
  expected: FormDeploymentManifest,
  validator: BoundFormValidator,
  limits: RuntimeLimits = defaultRuntimeLimits
): Promise<AdmittedFormRelease> {
  limits = { ...limits };
  for (const limit of Object.values(limits)) if (!Number.isSafeInteger(limit) || limit <= 0) throw new Error("Invalid admission limits.");
  // Snapshot all mutable inputs before the first asynchronous digest operation.
  const manifest = parse(JSON.stringify(expected), limits) as unknown as FormDeploymentManifest;
  const locales = { ...localeJson };
  const bound = { ...validator };
  if (manifest.formatVersion !== 1 || typeof manifest.retired !== "boolean" || manifest.retired
    || !nonempty(manifest.formId) || !nonempty(manifest.releaseId) || !Number.isSafeInteger(manifest.revision) || manifest.revision <= 0
    || !record(manifest.locales) || !record(manifest.validator)) throw new Error("Invalid or retired deployment manifest.");
  if (Object.keys(manifest.locales).length === 0 || Object.keys(locales).sort().join("\0") !== Object.keys(manifest.locales).sort().join("\0"))
    throw new Error("Locale artifacts do not match the trusted deployment.");
  if (typeof bound.validate !== "function" || !digest(bound.sha256) || !digest(bound.schemaSha256)
    || bound.sha256 !== manifest.validator.sha256 || bound.schemaSha256 !== manifest.validator.schemaSha256)
    throw new Error("The bundled validator does not match the trusted deployment.");
  const raw = parse(releaseJson, limits);
  await verify(releaseJson, manifest.releaseSha256);
  if (!record(raw.id) || raw.id.value !== manifest.releaseId || raw.retired !== false || !record(raw.candidate))
    throw new Error("Foreign or retired release.");
  const candidate = raw.candidate;
  if (!record(candidate.formId) || candidate.formId.value !== manifest.formId || !record(candidate.revision) || candidate.revision.value !== manifest.revision)
    throw new Error("Foreign form or revision.");
  for (const key of ["fields", "renderers", "translations", "actions", "diagnostics"]) if (!Array.isArray(candidate[key])) throw new Error(`Missing release ${key}.`);
  for (const [key, identity] of [["fields", "id"], ["renderers", "componentId"], ["actions", "actionId"]]) {
    const identities = new Set<string>();
    for (const value of candidate[key!] as unknown[]) {
      if (!record(value) || !nonempty(value[identity!])) throw new Error(`Invalid release ${key}.`);
      const id = key === "renderers" ? `${value[identity!]}@${value.versionRange}` : value[identity!] as string;
      if (identities.has(id)) throw new Error(`Duplicate release ${key}.`);
      identities.add(id);
      if (key === "fields" && (!nonempty(value.dataPath) || !value.dataPath.startsWith("/") || typeof value.required !== "boolean")) throw new Error("Malformed server field snapshot.");
      if (key === "renderers" && !nonempty(value.versionRange)) throw new Error("Malformed renderer requirement.");
      if (key === "actions" && (!nonempty(value.handlerId) || typeof value.requiresValidForm !== "boolean" || !record(value.label) || !nonempty(value.label.key))) throw new Error("Malformed action requirement.");
    }
  }
  if (!nonempty(raw.publishedAt) || !Array.isArray(raw.evidence) || raw.evidence.some(value => !nonempty(value))) throw new Error("Malformed publication metadata.");
  if (!digest(candidate.candidateSha256) || (candidate.diagnostics as unknown[]).some(item => !record(item) || item.severity === "error" || item.severity === 2))
    throw new Error("Invalid release candidate.");
  for (const key of ["dataSchema", "uiSchema"]) {
    const artifact = candidate[key];
    if (!record(artifact) || typeof artifact.content !== "string") throw new Error("Malformed schema artifact.");
    parse(artifact.content, limits);
    await verify(artifact.content, artifact.sha256);
  }
  if ((candidate.dataSchema as Record<string, unknown>).sha256 !== bound.schemaSha256) throw new Error("Validator belongs to a different schema.");
  const translations: Record<string, Readonly<Record<string, string>>> = Object.create(null);
  for (const [locale, hash] of Object.entries(manifest.locales)) {
    const content = locales[locale];
    if (typeof content !== "string") throw new Error("Missing locale artifact.");
    const dictionary = parse(content, limits);
    await verify(content, hash);
    if (Object.values(dictionary).some(value => typeof value !== "string")) throw new Error("Locale values must be strings.");
    for (const requirement of candidate.translations as unknown[]) {
      if (!record(requirement) || !nonempty(requirement.key) || typeof dictionary[requirement.key] !== "string") throw new Error("Missing required release translation.");
    }
    translations[locale] = Object.freeze(dictionary as Record<string, string>);
  }
  return Object.freeze({ release: freeze(raw) as unknown as FormRelease, translations: Object.freeze(translations), validate: bound.validate });
}

function record(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function nonempty(value: unknown): value is string { return typeof value === "string" && value.length > 0; }
function digest(value: unknown): value is string { return typeof value === "string" && /^[a-f0-9]{64}$/.test(value); }
async function verify(content: string, expected: unknown): Promise<void> {
  if (!digest(expected)) throw new Error("Invalid deployment digest.");
  const actual = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(content))), value => value.toString(16).padStart(2, "0")).join("");
  if (actual !== expected) throw new Error("Artifact differs from the trusted deployment digest.");
}
function parse(content: string, limits: RuntimeLimits): Record<string, unknown> {
  if (typeof content !== "string" || new TextEncoder().encode(content).byteLength > limits.maximumArtifactBytes) throw new Error("Admission byte limit exceeded.");
  const root: unknown = JSON.parse(content);
  if (!record(root)) throw new Error("Admission requires an object.");
  let nodes = 0;
  const stack = [{ value: root as unknown, depth: 1 }];
  while (stack.length) {
    const entry = stack.pop()!;
    if (++nodes > limits.maximumJsonNodes || entry.depth > limits.maximumJsonDepth) throw new Error("Admission graph limit exceeded.");
    if (typeof entry.value === "number" && !Number.isFinite(entry.value)) throw new Error("Nonfinite JSON value.");
    if (record(entry.value) || Array.isArray(entry.value)) for (const [key, value] of Object.entries(entry.value)) {
      if (["__proto__", "prototype", "constructor"].includes(key)) throw new Error("Unsafe artifact key.");
      stack.push({ value, depth: entry.depth + 1 });
    }
  }
  return root;
}
function freeze(value: unknown): unknown {
  if (record(value) || Array.isArray(value)) { for (const child of Object.values(value)) freeze(child); Object.freeze(value); }
  return value;
}
