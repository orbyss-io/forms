# Forms and localization implementation plan

Status: approved on 2026-09-06. This plan does not authorize publication or remote operations.

Frontend publication is fixed to GitHub Packages under `@orbyss`; the workflow will be enabled only
after the package set is complete. See `docs/frontend-package-publication.md`.

## Implementation progress

As of 2026-09-06:

- Slice 1 is implemented in the generated browser harness for Chromium, WebKit, phone, tablet,
  desktop, orientation, touch, reflow, RTL and theme coverage. Local Firefox launch remains blocked
  before page load by the Playwright 1.62.1 Windows bundle activation defect recorded in
  `docs/ui-experience-evidence.md`; CI retains the Firefox requirement.
- Slice 2 is complete: independent Forms and Localization semantic contracts, lifecycle,
  concurrency, idempotency, audit, wizard, icon, action, import and runtime ports compile with no
  implementation dependencies.
- Slice 3 is implemented through provider-neutral validation, deterministic JSON Schema/JSON Forms
  UI Schema compilation, renderer/action/translation manifests, compatibility analysis, and atomic
  digest-verified immutable filesystem release stores. AJV 2020-12 parity and hostile runtime
  artifact fixtures now exist in the isolated frontend workspace. Compiler-generated fixture
  exchange and bundled-helper browser acceptance remain part of the release-proof slice.
- Slice 4 has its framework-neutral foundation and first framework binding: JSON-safe runtime
  contracts, release-integrity and schema-bound checks, a renderer/action registry, AJV build-time
  standalone compilation, a dependency-free editor contract, the CodeMirror 6 default editor
  adapter, a separately installed exact-pinned Monaco adapter, and an exact-pinned React/JSON
  Forms adapter using a precompiled-validator facade rather than browser code generation. JSON Forms
  remains a peer boundary rather than a public contract. The React journey now has Chromium/WebKit
  desktop, phone and tablet acceptance; Firefox remains an unconditional Linux CI gate because the
  pinned local Windows browser bundle cannot launch. A compiler-emitted .NET release fixture is
  consumed byte-for-byte by the TypeScript integrity/runtime path, including the strict allowlist
  for Program Kit schema annotations. Vue/Angular bindings remain.
- Slice 5 now includes the portable wizard parser/state machine and React renderer: translated/icon
  navigation, progress/status semantics, validation-gated movement, optional and conditional steps,
  and application-owned completion callbacks. The provider-neutral action manifest, ordered action
  bar contract, framework-neutral controller and React renderer now add validation gates, trusted
  availability policy, single-flight execution, cancellation, public-safe failures and localized
  labels/icons. The dependency-free modeler core now provides a bounded provider-neutral document,
  atomic optimistic/idempotent commands, undo/redo and synchronized JSON/tree/graph projections.
  Its action catalog tells authors which trusted feature package or local contract supplies each
  handler. A framework-neutral searchable-lookup registry/controller now provides trusted source
  IDs, paging, dependent filters, cancellation, label rehydration and public-safe failures. React
  now has a separately installed semantic searchable-combobox renderer with paging and localized
  selected-label rehydration. The first responsive React modeler administration package now keeps
  its tree, field inspector, CodeMirror/native strict-CSP JSON source and relationship graph on the
  same optimistic session, with browser-tested selection, validation and undo. Its built-in palette
  atomically creates fields and matching controls, the block canvas remains synchronized, and a
  trusted application callback supplies live preview without executable document data. Installed
  component packages contribute immutable typed authoring contracts; their compatible value kinds,
  version range and allowlisted options appear in the inspector and invalid bindings block commit.
  Pointer drag/reparenting, Alt+Arrow and explicit touch/keyboard move controls now share the same
  validated optimistic move command; provider-neutral target discovery excludes cycles and leaf
  elements. The React adapter now also supplies a low-rank semantic core renderer suite for text,
  multiline text, number/integer, Boolean, date/time string input, single choice and multi-choice.
  Specialized and application renderers retain priority. Vue/Angular bindings remain.
- Slice 6 is complete: locale/fallback validation, structured scopes, ICU-style
  placeholder/plural/select checks, exact/fallback immutable resolution and deterministic bundles.
  The explicit Forms-to-Localization bridge adds missing catalog messages, preserves reviewed
  values and rejects conflicting source contracts. A dependency-free frontend management session
  now adds audited optimistic/idempotent inline mutations, undo/redo, ICU diagnostics and bounded
  locale/scope/form/state/missing/text projections. Its responsive React plane provides windowed
  inline editing, lifecycle permission gates and hash-bound import-preview review across the same
  strict-CSP browser/device matrix. Dependency-free CSV, JSON, XLSX, XLIFF 2.1 and PO adapters now
  support bounded deterministic import/export and feed a hash-bound preview/apply coordinator.
  Deterministic immutable-release diff contracts cover locale policy plus scoped message changes.
  The React plane now includes a responsive add-message dialog for structured scope, source text,
  context, description and typed ICU arguments; successful messages enter the missing-locale grid
  through the same audited session. Its bounded upload dialog now selects CSV, XLSX, JSON, XLIFF
  2.1 or PO, captures declarative semantic-column and locale mappings, merge policy and structured
  scope, and delegates bytes only to the trusted preview port. Independently selected CShells
  endpoint features now expose the authenticated management plane and cacheable immutable runtime
  plane without adding middleware or response policy to the Host. Provider-neutral application
  orchestration now closes the server path across catalog creation/replacement, bounded queries,
  hash-bound imports, review, approval, deterministic publication and retirement. Replaceable
  storage ports and the filesystem adapter add atomic optimistic writes, durable idempotency replay,
  append-only claim-attributed audit history, bounded enumeration/documents, verified payloads and
  separate retirement sidecars so immutable release content is never overwritten.
  Sixteen explicit closed-world Localization MCP tools now expose bounded queries, validation,
  hash-bound import preview/apply, deterministic export, lifecycle, release diff, and immutable
  runtime inspection through those same application services.
- Slice 7 now has its provider-neutral operational core and filesystem proof: owner-scoped
  resumable drafts, canonical bounded JSON, partial-save versus authoritative-submit validation,
  exact immutable-release binding, clean-attachment snapshots, withdrawal and separately
  authorized accept/reject lifecycle. Attachment storage is split into metadata, quarantine and
  promoted content with strict media/extension/signature policy, byte bounds, a replaceable
  fail-closed malware scanner and opaque provider keys. An endpoint-only submissions CShells
  feature streams binary content without choosing global error handling. Eleven explicitly registered
  closed-world MCP tools use the official C# SDK and the same application services; their stateless
  shared Streamable HTTP CShells feature requires the selected shell authentication policy and
  derives ownership from its validated principal. Draft migration compares the bound source and
  target releases: compatible changes can rebind directly, while breaking changes require a
  registered trusted migration handler and authoritative target validation. The management plane
  now adds durable editable
  aggregates, deterministic compilation, evidence-bound review, approval, immutable publication,
  retirement sidecars, compatibility queries, authenticated management endpoints, cacheable
  runtime endpoints, and twelve governed management MCP tools. The shared endpoint-only MCP
  transport composes independently selected Forms and Localization contributors without Host
  behavior. Complete bounded in-memory adapters now drive the public-contract, management HTTP,
  runtime, and shared MCP probes.
- Slice 8 now includes the established UI experience harness, package-isolation architecture checks,
  shell-portable frontend test entry point, real tarball payload inspection, and a disposable clean
  consumer that installs and imports all nineteen packages with their exact framework peers. The
  first Vue runtime binding shares the CSP-safe precompiled validation seam. The tagged GitHub
  Packages publication step, deeper Vue/Angular management parity, physical-device/manual assistive
  evidence and the already-recorded local Firefox limitation remain. No web behavior has been added
  to `ProgramKit.Host`. Production EF Core, SQLite, migration, and object-storage choices are
  deliberately deferred to consumers rather than becoming Program Kit defaults.

## Fixed decisions

- Program Kit owns framework-neutral form, localization, action, release and compatibility
  contracts. JSON Forms, AJV, CodeMirror and Monaco are adapters, never public domain contracts.
- Management theming is CSS-first and cross-framework: semantic custom properties define branding,
  spacing, typography, density, focus, shape, shadow and motion; stable `data-pk-slot` attributes
  and typed class maps allow targeted composition; optional component styles live in a low-priority
  cascade layer; and an unstyled mode preserves accessible markup without Program Kit classes.
- CodeMirror 6 is the unconditional rich JSON editor default. Monaco is a separately installed
  desktop enhancement behind the shared editor contract and must never become a transitive dependency of the default
  authoring experience. Because CodeMirror uses dynamic layout style attributes, deployments that
  prohibit all style attributes use the built-in native source editor; CSP is not weakened for an
  editor dependency.
- Phone, tablet and desktop support is mandatory. Responsive layout, touch input, orientation,
  browser-engine compatibility, enlarged-text reflow, RTL and reduced-motion behavior are release
  acceptance, not consumer-specific polish.
- Management and runtime boundaries are separate CShells features. The Host does not register form,
  localization, submission, editor or action middleware/endpoints.
- In-memory persistence is the deterministic test/development reference. It is never represented as
  durable. Filesystem persistence is an explicit adapter. Program Kit does not select a production
  database, ORM, migration system, or object-storage provider for consumers.
- Every mutation uses optimistic concurrency, an idempotency key and audit metadata. Published form
  and localization releases are immutable.
- Server-side validation and authorization remain authoritative. Schemas, UI schemas, translations,
  renderer options and actions are data; none may carry scripts, arbitrary callbacks or executable
  markup.

## Package topology

The .NET boundary is split into:

- `ProgramKit.Forms.Abstractions`: identifiers, authoring commands, immutable release contracts,
  diagnostics, compatibility manifests and narrow query ports.
- `ProgramKit.Forms.Core`: validation and release compatibility analysis.
- `ProgramKit.Forms.Application`: authoring, deterministic compilation, evidence-bound review,
  publication, bounded queries and retirement orchestration over replaceable stores.
- `ProgramKit.Forms.JsonForms`: compilation to JSON Schema/JSON Forms UI Schema, AJV parity fixtures
  and translation-requirement extraction.
- `ProgramKit.Forms.Storage.Abstractions`, `.InMemory` and `.FileSystem`: narrow consumer-owned
  persistence ports, a complete non-durable test/development reference, and an explicit filesystem
  adapter without leaking persistence models into application contracts.
- `ProgramKit.Forms.Web.Management` and `.Web.Runtime`: independently selected CShells features.
- `ProgramKit.Forms.Submissions`: optional drafts, resumability, attachments and submission
  lifecycle, including compatibility-aware migration through explicitly registered trusted
  handlers; form rendering does not imply data collection.
- `ProgramKit.Mcp.AspNetCore`: the single protected stateless Streamable HTTP transport, without
  domain tools or middleware ownership.
- `ProgramKit.Forms.Mcp.AspNetCore`, `.Tool`, `.Management.Mcp.AspNetCore` and `.Management.Tool`:
  independently selected tool contributors over the same application services, without a second
  rules engine or independently mapped MCP endpoints.
- `ProgramKit.Localization.Abstractions`, `.Core`, `.Formats`, `.Storage.*`, `.Web.Management`,
  `.Web.Runtime`, `.Application`, `.Mcp.AspNetCore` and `.Tool`: an independent application-wide
  localization bounded context.
- Format adapters for CSV, XLSX, JSON, XLIFF 2.1 and PO. Remote imports are a separately enabled,
  SSRF-hardened connector rather than a core URL field.

Frontend packages mirror those seams: contracts, JSON Forms adapter, renderer registry, governed
actions, wizard, CodeMirror editor, optional Monaco editor, form modeler, schema modeler,
localization management and the Program Kit design-system adapter. Framework adapters consume these
packages; business applications do not import management-plane internals.

## Canonical models and release flow

`FormDefinition` is the editable, provider-neutral aggregate. It contains stable field, layout,
step, translation, renderer and action references. It is not a one-to-one copy of JSON Schema or a
JSON Forms UI Schema. Compilation produces a candidate containing the target schemas, resolved
references, renderer/component manifest, translation-requirement manifest, action manifest,
diagnostics, hashes and deterministic test fixtures.

The lifecycle is `draft -> validate -> compile -> test -> review -> publish`. Publishing creates an
immutable `FormRelease`; runtime APIs serve releases, never mutable drafts. Saved data records the
form release that accepted it. Compatibility analysis reports breaking schema, renderer, action and
translation changes and requires an explicit migration for resumable drafts affected by a breaking
release.

`LocalizationCatalog` owns locales, structured scopes, messages, context, placeholders, provenance,
workflow state and fallback policy. `LocalizationRelease` is immutable and can be deployed
independently. Forms emit `TranslationRequirementManifest` entries and reference stable keys; they
do not own translation values. A form-local scope serializes as `forms:{formId}`, while APIs retain
the structured scope kind and resource identifier so clients can filter all forms or one selected
form without parsing strings.

Messages preserve typed arguments and plural/select behavior behind an adapter compatible with
Unicode/CLDR semantics. Locale identifiers use BCP 47. Language and direction metadata travel
together. Source/default text keeps a form usable when localization is not installed, while a
consumer may make locale completeness a publication policy.

## Program Kit wizard renderer

The built-in JSON Forms stepper remains a compatibility fallback only. The default Program Kit
wizard is a custom `Categorization` renderer selected through a Program Kit variant and renderer
manifest. Its stable contract includes:

- top, side and compact/mobile navigation; custom line, segment and progress treatments;
- registry-based icons, translated title/subtitle/status text and consumer design tokens;
- current, visited, completed, warning, error, skipped, optional and disabled states;
- linear, non-linear and visited-only navigation policies;
- validation gates, first-error focus, conditional steps and stable navigation when steps appear or
  disappear;
- Back, Next, Save draft, Skip, Cancel and Finish action references with busy/error semantics;
- resumable/deep-linked progress where policy allows it; and
- keyboard, touch, screen-reader, RTL, forced-colors and reduced-motion behavior.

Navigation cannot invoke arbitrary code from schema data. Applications register typed action
handlers; form releases reference allowlisted action identifiers and input/output contracts.
Reusable feature packages publish trusted action-contract metadata and register the executable
handler. Application-specific handlers may be registered locally. Handler IDs are stable contract
identities; an incompatible contract receives a new ID. Runtime preparation fails before rendering
when a release references a handler that the selected application packages did not register.

Searchable choices follow the same boundary. A field stores a stable data-source ID rather than a
URL, credential or callback. An installed lookup provider owns typed search, cursor paging,
dependent filters and stored-value label resolution. Protected or business data is retrieved through
a server feature with authorization; direct browser providers are restricted to explicitly
registered public CORS-safe sources. Submitted values are always revalidated server-side.
The React renderer is optional and uses combobox/listbox semantics, native keyboard focus, text-only
labels, live loading/failure status and an explicit load-more operation. Dependent filters are read
only from declared rooted data JSON Pointers.

## Authoring and localization experience

The form modeler provides a palette, layout canvas, property inspector, renderer/action binding,
live preview and synchronized human-tree, JSON and graph views. The JSON view defaults to CodeMirror
and shares parse, schema, completion and diagnostic services with optional Monaco. Switching editors
does not change the document or validation result.

The localization plane provides a virtualized inline-edit table with locale, scope, form, status,
missing-value and text filters; add/import/export actions; dry-run import mapping; conflict and merge
policies; placeholder/plural validation; source/target comparison; review/approval; immutable
publication; release diff; and missing/unused/duplicate key reports. Machine or AI suggestions, when
an adapter is installed, enter an explicit unreviewed state and are never silently published.

Forms integrate through narrow query ports: localization can resolve form display names for its
filter, and forms can request completeness/preview information. Neither core package references the
other implementation. An integration feature composes the two when both are selected.

## Security and operational boundaries

- External `$ref` values are resolved before runtime, bundled, size/depth bounded and hash-tracked.
- Remote schemas and UI schemas use a restricted allowlisted subset and never weaken CSP.
- Regex, collection, text, nesting, attachment and compilation limits are explicit policy.
- UI schema options and renderer IDs are allowlisted by the installed renderer manifest.
- Rich text and files are separate optional capabilities with sanitization, malware scanning,
  storage and retention contracts.
- Remote localization imports require HTTPS allowlists, redirect/DNS/IP validation, byte/time/type
  limits, provenance and content hashes. Runtime rendering never fetches arbitrary URLs.
- Management, review, publish, runtime, submission and export permissions are distinct.
- Audit data excludes secrets and submitted sensitive values; observability uses stable form,
  release, scope and diagnostic identifiers.

## Mandatory device and quality matrix

Core CI exercises Chromium, Firefox and WebKit. The pairwise matrix covers desktop, touch phone and
touch tablet profiles; portrait and landscape; 320 CSS-pixel reflow with 200% root text; light,
dark, forced-colors and reduced-motion modes; LTR and RTL; keyboard-only and touch navigation; and
no unexpected page-level horizontal overflow. Critical form and localization journeys run in each
engine. Renderer state galleries cover every control and wizard state.

Playwright device profiles are repeatable compatibility evidence, not proof for physical hardware,
virtual keyboards or assistive technologies. Release acceptance therefore also records manual
screen-reader and representative physical phone/tablet journey results. Consumer applications rerun
the same adapter suite against their actual framework, CSS system, browser support policy and CSP.

Accessibility, localization, performance and security checks include WCAG 2.2 AA automation,
focus/order/error announcements, touch target sizing, content expansion, locale formatting,
pseudo-localization, bidirectional isolation, large-form budgets, dependency/CSP inspection,
cross-engine validation parity and hostile-schema/import fixtures.

## Delivery slices

1. **UI contract hardening**: make the multi-device matrix normative and extend the generated UI
   acceptance harness beyond Chromium-only narrow-viewport approximation.
2. **Contracts**: canonical form/localization models, commands, queries, diagnostics, lifecycle,
   concurrency/idempotency/audit contracts and architecture tests.
3. **Compiler and storage**: JSON Forms compilation, translation manifests, compatibility analysis,
   immutable file-system stores and deterministic fixtures.
4. **Runtime**: JSON Forms runtime adapter, renderer registry, CodeMirror default and separately
   installable Monaco adapter.
5. **Authoring**: schema/form modelers, custom controls/actions and the Program Kit wizard.
6. **Localization**: management/runtime features, grid workflow, imports/exports, scopes, fallbacks,
   plural/select messages and forms integration.
7. **Operational capabilities**: resumable drafts, optional submissions/attachments, MCP/tool
   surfaces, complete in-memory reference persistence, and consumer-owned provider contracts.
8. **Release proof**: clean pack/install probes, cross-engine/device suites, security fixtures,
   upgrade/migration tests, evidence and consumer documentation.

Each slice must pass deterministic tests and clean package-isolation probes before the next slice
relies on it. No slice may add Host-owned middleware or use `InternalsVisibleTo` for its probes.
