export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { readonly [key: string]: JsonValue };
export type JsonObject = { readonly [key: string]: JsonValue };

export interface FormArtifact {
  readonly mediaType: string;
  readonly content: string;
  readonly sha256: string;
}

export interface FormRendererRequirement {
  readonly componentId: string;
  readonly versionRange: string;
}

export interface FormLocalizedTextReference {
  readonly key: string;
  readonly defaultText: string;
  readonly context?: string | null;
}

export interface FormIconReference {
  readonly name: string;
  readonly bundle?: string | null;
}

export interface FormTranslationRequirement {
  readonly key: string;
  readonly defaultText: string;
  readonly sourceLocale: string;
  readonly scope: string;
  readonly context?: string | null;
  readonly arguments?: readonly string[] | null;
}

export type FormActionKind = "back" | "next" | "saveDraft" | "skip" | "cancel" | "submit" | "custom";

export interface FormActionRequirement {
  readonly actionId: string;
  readonly handlerId: string;
  readonly kind: FormActionKind | number;
  readonly label: FormLocalizedTextReference;
  readonly requiresValidForm: boolean;
  readonly icon?: FormIconReference | null;
}

export type FormDiagnosticSeverity = "information" | "warning" | "error" | number;

export interface FormDiagnostic {
  readonly code: string;
  readonly severity: FormDiagnosticSeverity;
  readonly message: string;
  readonly path?: string | null;
}

export interface FormCandidate {
  /** Complete provider-neutral server field metadata, absent only on legacy candidates. */
  readonly fields?: readonly JsonObject[];
  readonly formId: { readonly value: string };
  readonly revision: { readonly value: number };
  readonly dataSchema: FormArtifact;
  readonly uiSchema: FormArtifact;
  readonly renderers: readonly FormRendererRequirement[];
  readonly translations: readonly FormTranslationRequirement[];
  readonly actions: readonly FormActionRequirement[];
  readonly diagnostics: readonly FormDiagnostic[];
  readonly compiledAt: string;
  readonly candidateSha256: string;
}

export interface FormRelease {
  readonly id: { readonly value: string };
  readonly candidate: FormCandidate;
  readonly publishedAt: string;
  readonly evidence: readonly string[];
  readonly retired: boolean;
}

/** Trusted deployment metadata. Distribute independently of any untrusted artifact input. */
export interface FormDeploymentManifest {
  readonly formatVersion: 1;
  readonly formId: string;
  readonly releaseId: string;
  readonly revision: number;
  /** SHA-256 of the complete UTF-8 release JSON, including server field metadata. */
  readonly releaseSha256: string;
  readonly locales: Readonly<Record<string, string>>;
  readonly validator: { readonly sha256: string; readonly schemaSha256: string };
  readonly retired: boolean;
}

/** Constructed by a trusted build from a verified, statically imported validator module. */
export interface BoundFormValidator {
  readonly sha256: string;
  readonly schemaSha256: string;
  readonly validate: OrbyssValidator;
}

export interface RuntimeLimits {
  readonly maximumArtifactBytes: number;
  readonly maximumJsonDepth: number;
  readonly maximumJsonNodes: number;
}

export interface RuntimeValidationIssue {
  readonly path: string;
  readonly keyword: string;
  readonly message: string;
  readonly property?: string;
}

export type OrbyssValidator = (data: JsonValue) => readonly RuntimeValidationIssue[];

export const defaultRuntimeLimits: RuntimeLimits = {
  maximumArtifactBytes: 1_048_576,
  maximumJsonDepth: 64,
  maximumJsonNodes: 100_000
};

/** A minimal translation port shared by framework-neutral form packages. */
export type OrbyssTranslator = (key: string, fallback: string, context?: string | null) => string;
