# Forms and localization implementation evidence

Evidence date: 2026-09-06

## Implemented package boundaries

- `ProgramKit.Forms.Abstractions` and `ProgramKit.Localization.Abstractions` contain only public
  semantic contracts and have no package or project dependencies.
- `ProgramKit.Forms.Core` provides bounded definition validation and release compatibility analysis.
- `ProgramKit.Forms.Application` implements authoring/query/lifecycle ports over replaceable
  stores. It applies durable replay before lifecycle preconditions, compiles exact revisions,
  binds explicit acceptance evidence to review, writes immutable release content before publishing
  aggregate state, and retains retirement separately.
- `ProgramKit.Forms.JsonForms` produces bundled JSON Schema 2020-12 and JSON Forms UI Schema,
  including the custom Program Kit wizard variant and deterministic renderer, translation and action
  manifests.
- `ProgramKit.Localization.Core` validates locale fallback graphs and ICU-style arguments,
  plural/select fallback branches, resolves immutable releases, and coordinates hash-bound import
  preview/apply operations with optimistic concurrency and idempotent replay. Its immutable-release
  differ reports locale-policy and scoped add/change/remove effects deterministically.
- `ProgramKit.Localization.Application` implements the public catalog management/query/lifecycle
  ports over replaceable storage. Create, replace, import, review, approval and publication use
  fingerprint-verified durable replay before lifecycle preconditions, so an exact retry remains
  idempotent after a process restart. Publication includes only source and approved localized
  values, enforces required-locale completeness, writes immutable content before marking the catalog
  published, and keeps release retirement separate from release content.
- `ProgramKit.Localization.Formats` provides bounded, dependency-free CSV, JSON, XLSX, XLIFF 2.1
  and singular PO import/export adapters. It rejects formula and macro input, unsafe XML, invalid
  digests, excessive archive expansion, unsupported PO plural conversion and XLIFF inline-code
  ambiguity. Export ordering and digests are deterministic; XLSX writes text-only cells.
- `ProgramKit.Forms.Localization` is the explicit cross-context bridge; neither semantic core gains
  a reverse dependency.
- `ProgramKit.Localization.Web.Management` is an endpoint-only `IWebShellFeature` for authenticated
  catalog queries/mutations, validation, bounded import preview/apply, deterministic export,
  release diff and lifecycle actions. Audit actors come from configured authenticated claims;
  clients cannot submit their own actor identity.
- `ProgramKit.Localization.Web.Runtime` is an independently selected endpoint-only
  `IWebShellFeature` for public-by-default or policy-protected immutable bundles and message
  resolution. It emits deterministic ETags, cache policy, `nosniff`, and conditional 304 responses.
- `ProgramKit.Forms.Web.Management` and `.Web.Runtime` are independently selected endpoint-only
  CShell features for authenticated lifecycle administration and immutable cacheable releases.
- `ProgramKit.Mcp.AspNetCore` owns the single authenticated stateless Streamable HTTP route. Forms
  operations, Forms management, and Localization are separate `IShellFeature` tool contributors;
  the transport owns no domain tools and contributors map no endpoints.
- Forms and Localization each expose editable aggregate, immutable release, and separate retirement
  ports with atomic filesystem adapters. Aggregate documents retain bounded append-only audit and durable command history,
  enforce opaque optimistic versions, and reject inconsistent internal metadata. Identifiers are
  hashed into filenames; payload envelopes are SHA-256 verified; exact release writes replay
  idempotently and conflicting overwrites fail closed.
- `ProgramKit.Forms.Storage.InMemory` implements every Forms persistence port, including attachment
  quarantine/content, while `ProgramKit.Localization.Storage.InMemory` implements all catalog and
  release ports. Both enforce bounds, detached copies, opaque optimistic versions, audit history,
  exact process-local replay, immutable release writes, and separate retirement state. They are the
  non-durable test/development reference and introduce no ORM, database, migration, cloud SDK, or
  web dependency.

The semantic, core, compiler, format, storage and bridge packages do not reference ASP.NET Core,
Entity Framework Core, CShells, CodeMirror, Monaco, AJV, or a JavaScript runtime. Each endpoint
package references only its bounded-context abstractions and private CShells ASP.NET abstractions.
The shared MCP transport references no domain package, and its domain contributors map no endpoint
or middleware. None reference `ProgramKit.Host`; the contexts remain independent except through the
explicit Forms-to-Localization bridge.

## Frontend runtime boundary

The isolated `src/typescript` workspace does not modify a consumer application's dependency graph.
It currently contains seventeen independently packable packages:

- `@orbyss/program-kit-forms-contracts`: dependency-free JSON-safe release and runtime contracts;
- `@orbyss/program-kit-forms-renderer-registry`: versioned renderer selection and declared-action
  dispatch without schema-supplied callbacks;
- `@orbyss/program-kit-forms-jsonforms-runtime`: release-integrity, size/depth/node, external
  reference, sensitive-key, renderer and action checks before an artifact reaches a UI binding;
- `@orbyss/program-kit-forms-ajv-build`: AJV 2020-12 validation and CSP-compatible standalone ESM
  generation for the build pipeline; and
- `@orbyss/program-kit-forms-codemirror`: the accessible CodeMirror 6 JSON editor adapter with JSON
  and external diagnostics; and
- `@orbyss/program-kit-ui-theme`: the dependency-free cross-framework visual contract with typed
  semantic token names, deterministic class composition, stable `data-pk-slot` conventions and an
  optional cascade-layered light/dark/automatic default theme; and
- `@orbyss/program-kit-forms-wizard`: the shared parser and state machine for validation-gated,
  conditional, optional, icon-bearing Program Kit wizard steps; and
- `@orbyss/program-kit-forms-actions`: the framework-neutral manifest-backed action-bar parser and
  controller with validation gates, trusted availability policy, single-flight dispatch,
  cancellation and public-safe failures; and
- `@orbyss/program-kit-forms-modeler`: the dependency-free provider-neutral authoring document and
  bounded transactional session with optimistic sequence checks, conflict-safe command replay,
  undo/redo, synchronized JSON serialization and graph projection, plus immutable component/action
  catalogs that expose installed package ownership and validate typed allowlisted bindings; and
- `@orbyss/program-kit-forms-modeler-react`: the optional responsive administration binding with a
  synchronized structure tree, property inspector, CodeMirror JSON source, strict-CSP native source
  fallback, field/layout palette, pointer drag targets, touch/keyboard reorder and reparent controls,
  block canvas, application-owned live preview and relationship graph. Its root and significant
  visual regions support consumer classes, stable slots and a per-instance unstyled mode; and
- `@orbyss/program-kit-forms-lookups`: trusted searchable source contracts and a framework-neutral
  controller for bounded search, cursor paging, declared dependent filters, cancellation, selected
  label rehydration and public-safe provider failures; and
- `@orbyss/program-kit-forms-lookups-react`: the optional semantic JSON Forms/React combobox binding
  for registered sources, with keyboard selection, paging, localized label rehydration and declared
  data-pointer filters; and
- `@orbyss/program-kit-forms-react`: the exact-pinned React 19/JSON Forms binding and semantic
  custom wizard and action-bar renderers, including conditional-step evaluation, AJV error-to-step
  mapping, localized action labels and consumer-owned icon rendering. It also provides low-rank,
  design-system-neutral text, multiline, numeric, Boolean, date/time, single-choice and multi-choice
  controls with an explicitly imported baseline stylesheet; consumer and specialized renderers can
  override them by rank; and
- `@orbyss/program-kit-forms-vue`: the exact-pinned Vue 3/JSON Forms binding over the same shared
  precompiled-validation facade, accepting consumer-selected renderer sets and emitting typed,
  framework-neutral data and validation changes. It supplies the same low-rank semantic text,
  multiline, numeric, Boolean, date/time, single-choice and multi-choice control baseline with an
  explicitly imported stylesheet; and
- `@orbyss/program-kit-forms-angular`: the exact-pinned Angular 22/JSON Forms standalone component,
  partial-compiled with Angular's compatible TypeScript 6 compiler, over the shared precompiled
  validator and typed framework-neutral change contract; and
- `@orbyss/program-kit-localization-management`: dependency-free structured localization scopes,
  locale/value workflow state, audited optimistic/idempotent commands, undo/redo, ICU diagnostics
  and bounded windowed row projections; and
- `@orbyss/program-kit-localization-management-react`: the optional responsive inline-edit grid,
  locale/scope/form/state/missing/text filters, lifecycle permission gates and hash-bound import
  preview surface, plus a validated add-message dialog for structured scope and typed ICU arguments
  and a bounded file/mapping dialog for CSV, XLSX, JSON, XLIFF 2.1 and PO preview submissions. Its
  table, filters, toolbar, dialogs, rows and import review expose the same theme slots and unstyled
  integration mode.

JSON Forms Core 3.8.0 is an exact peer dependency of the runtime boundary. The framework-neutral
package intentionally exposes JSON values rather than upstream framework types; React, Vue and
Angular bindings own those types and renderer integration. AJV is build-time-only for runtime
artifacts. CodeMirror is the unconditional rich-editor default, while Monaco is absent from both
manifests and the lockfile. CodeMirror's generated stylesheet accepts a caller-provided CSP nonce,
but its editor layout also relies on dynamic style attributes. The React modeler therefore provides
an explicit native source-editing mode for the stricter Program Kit policy that prohibits all style
attributes; the browser suite does not weaken CSP to accommodate an editor dependency.

JSON Forms 3.8 still exposes the withdrawn `Symbol.observable` in its TypeScript-5.8-era store
declarations, which TypeScript 7 rejects during third-party declaration checking. `skipLibCheck` is
therefore quarantined to the JSON Forms framework adapter projects only. The workspace default and
all framework-neutral packages retain full declaration checking, and the validator rejects any
additional quarantine.

The React, Vue and Angular bindings host JSON Forms with a shared precompiled-validator facade. Root validation delegates
to the generated validator, and visibility conditions use a bounded interpreter for `const`, `enum`,
JSON types, logical composition, required properties and property schemas. An unknown condition or
renderer-requested subschema keyword fails closed instead of compiling code in the browser. The real
React/JSON Forms server-render acceptance passes while both global `eval` and dynamic `Function`
construction are replaced with throwing functions.

The committed npm v3 lockfile is produced and exercised using the repository-managed exact Node
24.20.0 and npm 11.19.0 toolchain. Generated standalone validator modules are checked for `eval` and
`new Function`; modules containing AJV runtime helpers must be bundled before browser delivery.
The committed `dotnet-registration-release.json` fixture is regenerated semantically by the .NET
compiler probe and then consumed by the TypeScript integrity, AJV, action-dispatch and action-bar
paths. Strict AJV explicitly recognizes only `x-i18n` and `x-description-i18n`; arbitrary unknown
schema extensions continue to fail compilation.

## Forms browser acceptance

`tests/validate_forms_browser.py` builds a production React/JSON Forms fixture with esbuild 0.28.2
and a generated standalone validator, then serves it with a strict CSP that excludes inline script,
inline style, `eval` and dynamic `Function` construction. Playwright 1.62.1 and axe 4.13.0 verify:

- release-manifest actions render in declared order, block invalid submit attempts, dispatch through
  the trusted application port and replace unexpected exception details with a generic public error;
- asynchronous searchable choices page through a registered source, select through native
  combobox/listbox semantics and rehydrate the chosen label after an RTL locale switch;
- the responsive modeler synchronizes inspector changes into its tree and JSON source, rejects an
  invalid replacement document, restores edits through undo, exposes trusted action-package
  ownership, atomically adds a field/control from its palette, renders an application-owned preview,
  validates typed installed renderer options before commit, reorders/reparents through pointer or
  touch/keyboard-safe controls, rejects cyclic/leaf targets and projects relationships into the graph;
- semantic text, multiline, integer, Boolean, single-choice and multi-choice renderers preserve
  typed values and remain lower-ranked than the installed searchable-lookup renderer;
- localization rows filter by structured form scope and target locale, missing Arabic values edit
  with RTL direction, audited changes enter undo history, completed rows leave the missing-only
  projection, a typed-argument ICU message can be added through the responsive dialog, and a
  reviewed hash-bound import preview invokes only its trusted application port, while bounded file
  bytes, format, merge policy, structured scope and declarative column mappings pass through the
  upload dialog without browser parsing or executable schema data;
- validation blocks forward movement and maps errors to the owning step;
- conditional and optional steps appear, skip and complete correctly;
- a live English-to-Arabic switch preserves the active step, applies RTL and translates navigation;
- Home/End and direction-aware arrow navigation use native buttons and stable focus targets;
- semantic navigation, progress, active-region relationships and the complete journey have no
  automated WCAG 2.2 A/AA violations;
- visible actions meet 44-by-44 CSS-pixel sizing, reduced motion removes transitions, and the page
  reflows without horizontal overflow at 320 CSS pixels with 200% root text; and
- requests remain same-origin and console/page CSP violations fail the run.

Local Chromium passed desktop, phone portrait and phone landscape. Local WebKit passed desktop,
tablet portrait and tablet landscape. Playwright's pinned Windows Firefox executable still fails at
process launch with `spawn UNKNOWN`, before page load; the default CI/release command continues to
require Firefox on Linux. WebKit screenshots are intentionally omitted because Playwright injects
an inline stylesheet while capturing them; structured WebKit evidence remains strict-CSP, while
Chromium captures visual evidence.

## Deterministic acceptance

`tests/dotnet/ProgramKit.Forms.Localization.Contracts.Probe` verifies:

- valid and invalid form definitions, rooted JSON Pointer escaping, type-applicable constraints,
  translation-key consistency, layout references and wizard metadata;
- deterministic schema and UI Schema hashes, custom wizard renderer requirements, scoped
  translation requirements, action manifests, a cross-runtime release fixture and target
  path-collision rejection;
- compatibility classification for requiredness and tightened constraints;
- locale catalog validation, plural `other` requirements, plural argument typing, exact resolution,
  explicit source fallback and deterministic bundle hashes;
- bounded CSV long/wide, JSON, XLSX, XLIFF 2.1 and PO import/export round trips,
  formula/macro/XML/digest safeguards, deterministic formula-free XLSX output, hash-bound import
  previews, merge effects, optimistic concurrency and idempotent application;
- deterministic immutable-release differences for locale additions/removals/policy changes and
  scoped message additions/removals/content changes;
- durable application orchestration across create, import, version-bearing detail/search, review,
  approval, deterministic publication and separate retirement state, including stale-write and
  idempotency-key-reuse rejection plus exact import/lifecycle/publication/retirement replay after
  constructing fresh service and coordinator instances, plus required-locale failure, bounded
  catalog enumeration and catalog-envelope tamper rejection;
- atomic filesystem round-trips, idempotent writes, bounded enumeration and immutable overwrite
  rejection for both release types;
- explicit cross-context merging that adds missing form messages, preserves human-reviewed values,
  advances revisions only on success and rejects source-contract conflicts; and
- semantic-core and adapter dependency isolation without `InternalsVisibleTo`.

`tests/dotnet/ProgramKit.Localization.Web.Probe` verifies authenticated management access,
claim-derived audit attribution, decoded and pre-binding request-body limits, import preview/apply,
deterministic export, anonymous immutable runtime reads, ETags and conditional 304 responses. The
architecture validator also proves both packages remain endpoint-only CShells features and that
`ProgramKit.Host` contains no localization web reference.

`tests/dotnet/ProgramKit.Forms.Operations.Probe` verifies the optional data-collection layer through
public contracts: durable create replay after service reconstruction, owner isolation, stale-save
rejection, canonical partial drafts, required-field submission enforcement, clean attachment
quarantine/signature/scan/promotion, signature rejection, content isolation, exact attachment
snapshotting, non-editable submitted drafts, durable submit replay, withdrawal, separately
authorized acceptance, compatibility-aware rebind, breaking-change rejection, trusted migration,
target validation, exact migration replay, append-only audit history and tamper rejection. Its loopback web host proves
anonymous requests receive `401` from both the form API and MCP endpoint, then uses the same fixture
authentication scheme through the official MCP client to discover and invoke the tools. It also
proves eleven unique explicit tools expose neither actor, administrative review, binary transfer nor
scanner authority.

`tests/dotnet/ProgramKit.Forms.Management.Probe` verifies durable form creation and replay after
service reconstruction, deterministic compilation, evidence-bound review, approval, publication,
stale-write rejection, separate retirement, envelope-tamper rejection, runtime ETags and conditional
`304` responses. Its loopback host proves anonymous management and MCP calls receive `401`, then
uses the official MCP client to discover all twelve Forms management and sixteen Localization tools
on one shared route and invoke tools from both contributors. The loopback management/runtime/MCP
host uses the in-memory adapters while the same probe retains independent filesystem restart and
tamper evidence.

`tests/dotnet/ProgramKit.Storage.InMemory.Probe` exercises all in-memory stores through public
contracts: detached state, exact and conflicting replay, stale concurrency, bounded enumeration,
audit, immutable overwrite rejection, separate retirement, draft/submission and attachment metadata,
quarantine/promotion/content integrity/deletion, and Forms/Localization parity.

The MCP adapter uses the official `ModelContextProtocol` and `ModelContextProtocol.AspNetCore` 2.2.0
packages. Streamable HTTP is stateless and endpoint-only. Authentication remains normal Program Kit
API composition: the selected shell profile owns scheme/middleware/token validation, the MCP route
requires the host default policy or a named policy (including canonical `permission:*` policies),
and tool ownership is derived from the resulting `ClaimsPrincipal`. A cookie/BFF profile also
imposes its antiforgery protocol on MCP POSTs; bearer is the normal remote MCP composition.

Verified commands and results:

- `dotnet build ProgramKit.slnx -c Release --no-restore`: 65 projects, 0 warnings, 0 errors.
- `dotnet pack ProgramKit.slnx -c Release --no-build --no-restore`: all new package projects packed;
  warnings were limited to the intentionally non-packable Host and probe projects.
- `python tests/validate_forms_localization_contracts.py`: passed.
- `python tests/validate_forms_operations.py`: operational services, persistence, attachment
  isolation, governed migration, endpoint-only composition and authenticated MCP loopback passed.
- `python tests/validate_forms_management.py`: Forms application/storage, endpoint isolation,
  shared MCP contributor composition and authenticated official-client loopback passed.
- `python tests/validate_inmemory_storage.py`: complete dependency-free in-memory Forms and
  Localization persistence contract probe passed.
- `python tests/validate_forms_frontend.py --renew-lock --install`: strict TypeScript build, AJV parity and
  standalone-CSP checks, artifact/renderer/action/translation security tests, CodeMirror default
  checks, wizard/action navigation and state, modeler transactions/React administration/graph
  projection, lookup paging/cancellation/safe failures, localization optimistic/filter/import-preview
  behavior, rendered React binding tests, and fourteen workspace package
  dry-run packs passed.
- `python tests/validate_forms_frontend_packages.py`: seventeen real npm archives contained their
  declared JavaScript, TypeScript declarations and exported styles; a disposable consumer installed
  the archives with exact JSON Forms/React/Vue/Angular peers and imported every public package successfully.
- `python tests/validate_forms_browser.py --engines chromium,webkit`: six Chromium desktop/phone and
  WebKit desktop/tablet profiles passed locally, including governed action execution, searchable
  lookup paging/selection/localized rehydration, strict-CSP modeler and localization management,
  responsive card-table reflow and safe-error acceptance.
- `python tests/validate_dotnet_build_contract.py`: restricted-profile restore/build contract passed.
- `python tests/validate_dotnet_runtime.py`: runtime versions and package locks coherent.
- `python tests/validate_release_install.py`: packaged component and bundle clean-install test passed.
- `git diff --check`: passed.

The deterministic validator runs in `.github/workflows/dotnet-ci.yml` after the Release build and in
`scripts/Test-ProgramKit.ps1`. No paid live bootstrap acceptance was requested or run.
