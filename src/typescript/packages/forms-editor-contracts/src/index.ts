export interface JsonEditorDiagnostic {
  readonly from: number;
  readonly to: number;
  readonly severity: "info" | "warning" | "error";
  readonly message: string;
}

export interface JsonEditorOptions {
  readonly parent: HTMLElement;
  readonly document: string;
  readonly accessibleLabel: string;
  /** Nonce for adapter-owned style elements. It never authorizes arbitrary inline script. */
  readonly cspNonce?: string;
  readonly readOnly?: boolean;
  readonly onChange?: (document: string) => void;
  readonly diagnostics?: (document: string) => readonly JsonEditorDiagnostic[];
}

export interface JsonEditorHandle {
  readonly getDocument: () => string;
  readonly setDocument: (document: string) => void;
  readonly focus: () => void;
  readonly destroy: () => void;
}

/** A trusted, application-installed editor implementation. Form documents never select adapters. */
export interface JsonEditorAdapter {
  readonly id: string;
  readonly displayName: string;
  readonly requiresStyleAttributes: boolean;
  readonly requiresWorkers: boolean;
  readonly mount: (options: JsonEditorOptions) => JsonEditorHandle;
}

export function requireJsonEditorOptions(options: JsonEditorOptions): void {
  if (options.accessibleLabel.trim().length === 0) {
    throw new Error("A JSON editor requires an accessible label.");
  }
}

export function normalizeJsonEditorDiagnostics(
  diagnostics: readonly JsonEditorDiagnostic[],
  documentLength: number
): readonly JsonEditorDiagnostic[] {
  if (!Number.isSafeInteger(documentLength) || documentLength < 0) {
    throw new Error("The JSON editor document length must be a non-negative safe integer.");
  }
  return Object.freeze(diagnostics.map(diagnostic => {
    if (!Number.isSafeInteger(diagnostic.from) || !Number.isSafeInteger(diagnostic.to)) {
      throw new Error("JSON editor diagnostic offsets must be safe integers.");
    }
    if (diagnostic.message.trim().length === 0) {
      throw new Error("A JSON editor diagnostic requires a message.");
    }
    if (diagnostic.severity !== "info" && diagnostic.severity !== "warning" && diagnostic.severity !== "error") {
      throw new Error("A JSON editor diagnostic has an unsupported severity.");
    }
    const from = Math.min(documentLength, Math.max(0, diagnostic.from));
    const to = Math.min(documentLength, Math.max(from, diagnostic.to));
    return Object.freeze({ ...diagnostic, from, to });
  }));
}
