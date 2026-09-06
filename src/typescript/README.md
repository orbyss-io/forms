# Program Kit frontend packages

This isolated workspace contains framework-neutral form-runtime packages. It is not injected into a
consumer npm graph. Consumers install only the adapters they select.

The form-modeler, schema-modeler and localization-management UI prototypes were rejected during
physical review and removed from this workspace. They are not publishable packages. Server-side
form/localization contracts, validation, management APIs and MCP operations remain in the .NET
family.

- `forms-contracts` contains JSON-safe release types.
- `forms-renderer-registry` owns allowlisted renderer and action resolution.
- `forms-jsonforms-runtime` verifies immutable releases, adapts translations without suppressing
  JSON Forms validation messages, and prepares a framework binding.
- `forms-ajv-build` validates JSON Schema 2020-12 at build time. Runtime consumers receive a
  prebuilt validator and do not require unsafe dynamic code evaluation.
- `forms-editor-contracts` keeps reusable JSON-editor consumers independent from a particular
  editor. `forms-codemirror` is the default; `forms-monaco` is separately installable. Both use
  two-space indentation and make Tab indent by default.
- `forms-wizard` owns navigation, validation, conditional-step, progress and status behavior.
- `forms-actions` owns manifest-backed action parsing, validation gates, availability,
  single-flight execution, cancellation and public-safe failure state.
- `forms-lookups` owns trusted searchable data-source contracts, bounded/cancellable queries,
  paging, dependent filters, selected-label rehydration and public-safe loading state.
- `forms-lookups-react` is the optional JSON Forms/React searchable-combobox renderer.
- `forms-react`, `forms-vue` and `forms-angular` are the framework adapters. React and Vue ship
  semantic native-control styling; Angular composes with its consumer-selected renderers.
- `ui-theme` supplies optional semantic light/dark/automatic theme tokens.

Invalid controls expose inline messages, `aria-invalid`, `aria-describedby`, and a visible
danger-state outline. Consumer branding may override semantic tokens without removing those
accessibility states.
