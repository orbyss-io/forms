# Program Kit frontend packages

This isolated workspace contains framework-neutral frontend runtime packages. It is not injected
into a consumer npm graph. Consumers install only the adapters they select.

- `forms-contracts` contains JSON-safe release types.
- `forms-renderer-registry` owns allowlisted renderer and action resolution.
- `forms-jsonforms-runtime` verifies and prepares immutable releases for a framework binding.
- `forms-ajv-build` validates JSON Schema 2020-12 during build/test; runtime consumers receive a
  prebuilt validator and do not require unsafe dynamic code evaluation. Generated modules that
  reference AJV runtime helpers must be bundled before browser delivery; raw generated source is not
  itself the deployment artifact.
- `forms-editor-contracts` keeps modelers independent from a specific editor. `forms-codemirror` is
  the unconditional default JSON editor adapter, while `forms-monaco` is an exact-pinned optional
  package and Monaco remains outside every default consumer graph. Both rich editors need runtime
  layout style attributes. Both use a fixed two-space indentation policy and make Tab indent by
  default; `Ctrl+M` toggles focus-navigation mode for keyboard users. The React
  modeler exposes a native strict-CSP editing mode for deployments whose policy prohibits them.
- `forms-wizard` parses the compiled Program Kit `Categorization` variant and owns shared navigation,
  validation, conditional-step, progress and status behavior for every framework renderer.
- `forms-actions` parses action-bar references against immutable release requirements and owns
  validation gates, authorization visibility, single-flight execution, cancellation and public-safe
  failure state without automatic mutation retries.
- `forms-modeler` owns the bounded provider-neutral authoring document, atomic multi-view commands,
  optimistic sequence checks, idempotent command replay, undo/redo and graph projection shared by
  the human tree, JSON and visual graph editors. Immutable action/component catalogs identify the
  installed provider package and validate compatible value kinds, versions and typed option values.
- `forms-modeler-react` is the optional responsive administration binding. It keeps the structure
  tree, property inspector, CodeMirror JSON source and relationship graph on one governed modeler
  session, with a field/layout palette, block canvas, application-owned preview, selection,
  validation and undo/redo synchronized across views.
- `forms-modeler-vue` supplies the same governed form-modeler session, palette, structure, canvas,
  inspector, preview, JSON editor and graph through Vue-native events and rendering. It preserves
  explicit touch/keyboard reordering, optional pointer dragging, strict-CSP editing and theme slots.
- `forms-modeler-angular` is the Angular 22 standalone binding over the same governed session and
  catalogs. It provides the palette, structure, canvas, inspector, application-owned `TemplateRef`
  preview, JSON editor and graph with partial compilation and strict template checking.
- `forms-schema-modeler` owns the independent bounded JSON Schema 2020-12 authoring model.
  `forms-schema-modeler-react` and `forms-schema-modeler-vue` provide synchronized, themeable
  tree/canvas/editor/graph planes over that same governed session without duplicating schema rules.
  `forms-schema-modeler-angular` provides the equivalent Angular 22 standalone plane and shares the
  same injected CodeMirror/Monaco adapter contract and strict-CSP native fallback.
- `forms-lookups` owns trusted searchable data-source contracts, bounded/cancellable queries,
  paging, dependent filters, selected-label rehydration and public-safe loading state without
  embedding URLs, credentials or executable fetch logic in form schemas.
- `forms-lookups-react` is the optional JSON Forms/React searchable combobox renderer. It consumes
  registered lookup contracts, native data-pointer filter bindings and text-only results; consumers
  without remote choices do not inherit this package.
- `forms-react` is the first framework binding. It registers the Program Kit wizard with JSON Forms,
  renders semantic native navigation/progress/actions, evaluates conditional steps from JSON Forms
  state and exposes stable class/data hooks to the consumer-selected design-system adapter.
- `localization-management` mirrors the provider-neutral .NET localization semantics in a
  dependency-free browser session: structured scopes/locales/value states, audited optimistic and
  idempotent edits, undo/redo, ICU contract diagnostics, missing-value projection and bounded
  windowed filters.
- `localization-management-react` is the optional responsive management plane with inline editing,
  locale/scope/form/state/text filters, lifecycle permission gates, structured message creation,
  bounded import file/mapping submission, hash-bound preview review and a card reflow for phone and
  enlarged-text layouts. Parsing, authorization, conflict resolution and mutation remain server
  responsibilities.
- `localization-management-vue` provides the equivalent Vue management plane over the same audited
  session: scoped filters, bounded paging, inline editing, lifecycle gates, add-message/ICU authoring,
  bounded import preview/review/apply, stable theme slots and application-owned integration callbacks.
- `localization-management-angular` provides the equivalent Angular 22 standalone management plane
  over the same audited session and application-owned import ports, with partial compilation and
  strict template checking.
