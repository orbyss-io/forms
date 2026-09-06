import { json, jsonParseLinter } from "@codemirror/lang-json";
import { linter, type Diagnostic } from "@codemirror/lint";
import { basicSetup, EditorView } from "codemirror";

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
  /** Nonce applied to CodeMirror's generated style element. Runtime layout still uses style attributes. */
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

export function mountJsonEditor(options: JsonEditorOptions): JsonEditorHandle {
  if (options.accessibleLabel.trim().length === 0) {
    throw new Error("A JSON editor requires an accessible label.");
  }
  let applyingExternalDocument = false;
  const extensions = [
    basicSetup,
    json(),
    linter(jsonParseLinter()),
    EditorView.contentAttributes.of({ "aria-label": options.accessibleLabel }),
    EditorView.lineWrapping,
    EditorView.editable.of(options.readOnly !== true)
  ];
  if (options.cspNonce !== undefined && options.cspNonce.length > 0) {
    extensions.push(EditorView.cspNonce.of(options.cspNonce));
  }
  if (options.diagnostics !== undefined) {
    extensions.push(linter(view => options.diagnostics?.(view.state.doc.toString()).map(toDiagnostic) ?? []));
  }
  if (options.onChange !== undefined) {
    extensions.push(EditorView.updateListener.of(update => {
      if (update.docChanged && !applyingExternalDocument) options.onChange?.(update.state.doc.toString());
    }));
  }
  const view = new EditorView({ parent: options.parent, doc: options.document, extensions });
  return {
    getDocument: () => view.state.doc.toString(),
    setDocument: document => {
      if (document === view.state.doc.toString()) return;
      applyingExternalDocument = true;
      try {
        view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: document } });
      } finally {
        applyingExternalDocument = false;
      }
    },
    focus: () => view.focus(),
    destroy: () => view.destroy()
  };
}

function toDiagnostic(value: JsonEditorDiagnostic): Diagnostic {
  return {
    from: value.from,
    to: value.to,
    severity: value.severity,
    message: value.message
  };
}
