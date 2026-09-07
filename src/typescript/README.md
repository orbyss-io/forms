# Orbyss Forms frontend forms engine

This isolated workspace contains framework-neutral form-engine packages and thin JSON Forms
bindings. It is not injected into a consumer npm graph. Consumers install only the engine seams
they need and bring their own renderer components, editor implementation, CSS and design system.

Orbyss Forms does not publish form-modeler, schema-modeler, localization-management, searchable
select, CodeMirror, Monaco, core-control, action-bar or wizard UI components. Server-side
form/localization contracts, validation, management APIs and MCP operations remain in the .NET
family.

- `forms-contracts` contains JSON-safe release types.
- `forms-renderer-registry` owns allowlisted renderer and action resolution.
- `forms-jsonforms-runtime` verifies immutable releases, preserves validation translations and
  prepares a framework binding without runtime code generation.
- `forms-ajv-build` validates JSON Schema 2020-12 and generates CSP-compatible standalone
  validators during the build.
- `forms-editor-contracts` defines a dependency-free port for application-selected JSON editors.
- `forms-wizard` owns the framework-neutral navigation, validation and progress state machine.
- `forms-actions` owns manifest-backed action parsing, validation gates, availability,
  single-flight execution, cancellation and public-safe failure state.
- `forms-lookups` owns trusted searchable-source contracts, bounded/cancellable queries, paging,
  dependent filters, label rehydration and public-safe loading state.
- `forms-react`, `forms-vue` and `forms-angular` are thin JSON Forms integration packages. They
  connect governed schemas, translations and precompiled validation to renderers supplied by the
  consuming application; they contain no controls or CSS.
- `ui-theme` supplies optional application-wide semantic light/dark/automatic theme tokens. It is
  not a form component library.

Validation issues are always calculated. The bindings default to JSON Forms
`ValidateAndHide`; an application changes the binding to `ValidateAndShow` after its own submit,
wizard transition or other validation-triggering action. The application-owned renderer is
responsible for accessible inline errors, `aria-invalid`, `aria-describedby`, focus handling and
visible danger states.
