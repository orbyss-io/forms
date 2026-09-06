import { json, jsonParseLinter } from "@codemirror/lang-json";
import { indentWithTab } from "@codemirror/commands";
import { indentUnit } from "@codemirror/language";
import { linter, type Diagnostic } from "@codemirror/lint";
import { keymap } from "@codemirror/view";
import { basicSetup, EditorView } from "codemirror";
import {
  jsonEditorIndentationPolicy,
  normalizeJsonEditorDiagnostics,
  requireJsonEditorOptions,
  type JsonEditorAdapter,
  type JsonEditorDiagnostic,
  type JsonEditorHandle,
  type JsonEditorOptions
} from "@orbyss/program-kit-forms-editor-contracts";

export type { JsonEditorAdapter, JsonEditorDiagnostic, JsonEditorHandle, JsonEditorOptions } from "@orbyss/program-kit-forms-editor-contracts";

export const codeMirrorJsonEditorAdapter: JsonEditorAdapter = Object.freeze({
  id: "program-kit.codemirror-json",
  displayName: "CodeMirror",
  requiresStyleAttributes: true,
  requiresWorkers: false,
  mount: mountJsonEditor
});

export function mountJsonEditor(options: JsonEditorOptions): JsonEditorHandle {
  requireJsonEditorOptions(options);
  let applyingExternalDocument = false;
  const extensions = [
    basicSetup,
    json(),
    indentUnit.of(" ".repeat(jsonEditorIndentationPolicy.tabSize)),
    keymap.of([indentWithTab]),
    linter(jsonParseLinter()),
    EditorView.contentAttributes.of({ "aria-label": options.accessibleLabel }),
    EditorView.lineWrapping,
    EditorView.editable.of(options.readOnly !== true)
  ];
  if (options.cspNonce !== undefined && options.cspNonce.length > 0) {
    extensions.push(EditorView.cspNonce.of(options.cspNonce));
  }
  if (options.diagnostics !== undefined) {
    extensions.push(linter(view => normalizeJsonEditorDiagnostics(options.diagnostics?.(view.state.doc.toString()) ?? [], view.state.doc.length).map(toDiagnostic)));
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
