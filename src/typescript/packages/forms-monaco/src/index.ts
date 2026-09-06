import * as monaco from "monaco-editor";
import {
  normalizeJsonEditorDiagnostics,
  requireJsonEditorOptions,
  type JsonEditorAdapter,
  type JsonEditorDiagnostic,
  type JsonEditorHandle,
  type JsonEditorOptions
} from "@orbyss/program-kit-forms-editor-contracts";

export type { JsonEditorAdapter, JsonEditorDiagnostic, JsonEditorHandle, JsonEditorOptions } from "@orbyss/program-kit-forms-editor-contracts";

const markerOwner = "program-kit-json-editor";

export const monacoJsonEditorAdapter: JsonEditorAdapter = Object.freeze({
  id: "program-kit.monaco-json",
  displayName: "Monaco",
  requiresStyleAttributes: true,
  requiresWorkers: true,
  mount: mountMonacoJsonEditor
});

/**
 * Mounts the optional Monaco implementation. The consuming application remains responsible for
 * bundling same-origin Monaco workers; Program Kit never falls back to a CDN or a remote worker.
 */
export function mountMonacoJsonEditor(options: JsonEditorOptions): JsonEditorHandle {
  requireJsonEditorOptions(options);
  let applyingExternalDocument = false;
  const model = monaco.editor.createModel(options.document, "json");
  const editor = monaco.editor.create(options.parent, {
    model,
    ariaLabel: options.accessibleLabel,
    automaticLayout: true,
    readOnly: options.readOnly === true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    wordWrap: "on"
  });

  const applyDiagnostics = (): void => {
    const diagnostics = normalizeJsonEditorDiagnostics(options.diagnostics?.(model.getValue()) ?? [], model.getValueLength());
    monaco.editor.setModelMarkers(model, markerOwner, diagnostics.map(diagnostic => toMarker(model, diagnostic)));
  };
  applyDiagnostics();
  const subscription = editor.onDidChangeModelContent(() => {
    applyDiagnostics();
    if (!applyingExternalDocument) options.onChange?.(model.getValue());
  });

  return {
    getDocument: () => model.getValue(),
    setDocument: document => {
      if (document === model.getValue()) return;
      applyingExternalDocument = true;
      try { model.setValue(document); }
      finally { applyingExternalDocument = false; }
    },
    focus: () => editor.focus(),
    destroy: () => {
      subscription.dispose();
      monaco.editor.setModelMarkers(model, markerOwner, []);
      editor.dispose();
      model.dispose();
    }
  };
}

function toMarker(model: monaco.editor.ITextModel, diagnostic: JsonEditorDiagnostic): monaco.editor.IMarkerData {
  const start = model.getPositionAt(diagnostic.from);
  const end = model.getPositionAt(diagnostic.to);
  return {
    startLineNumber: start.lineNumber,
    startColumn: start.column,
    endLineNumber: end.lineNumber,
    endColumn: end.column,
    severity: severity(diagnostic.severity),
    message: diagnostic.message
  };
}

function severity(value: JsonEditorDiagnostic["severity"]): monaco.MarkerSeverity {
  if (value === "error") return monaco.MarkerSeverity.Error;
  if (value === "warning") return monaco.MarkerSeverity.Warning;
  return monaco.MarkerSeverity.Info;
}
