# Forms and localization implementation plan

Status: approved on 2026-09-06. This plan does not authorize publication or remote operations.

Frontend publication is fixed to GitHub Packages under `@orbyss`; the workflow will be enabled only
after the package set is complete. See `docs/frontend-package-publication.md`.

## Physical-review decision

The form journey was accepted, subject to corrected inline validation presentation. The TypeScript
form-modeler, schema-modeler and localization-management packages failed physical review and have
been removed from the publishable family. Program Kit retains the backend contracts, validation,
management APIs, storage ports and MCP operations; it does not ship a management UI. This decision
supersedes historical management-UI progress notes in the original approved plan.

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
  for Program Kit schema annotations. Vue and Angular runtime bindings now exist.
- Slice 5 includes the portable wizard parser/state machine and React renderer: translated/icon
  navigation, progress/status semantics, validation-gated movement, optional and conditional steps,
  plus manifest-backed actions with safe failure handling. Trusted searchable lookups provide
  paging, dependent filters, cancellation and label rehydration. React supplies low-rank semantic
  native controls that remain overrideable by application renderers.
- Slice 6 is complete on the server: locale/fallback validation, structured scopes, ICU-style
  placeholder/plural/select checks, exact/fallback immutable resolution, deterministic bundles,
  bounded CSV/JSON/XLSX/XLIFF/PO adapters, hash-bound imports and authenticated CShells/MCP
  management surfaces. No frontend localization-management package is shipped.
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
- Slice 8 includes the established UI experience harness, package-isolation architecture checks,
  shell-portable frontend tests, real tarball inspection, a disposable consumer of all fifteen
  packages, and read-only Chromium/Firefox/WebKit CI. Physical acceptance covers the form journey;
  management UI prototypes were removed after review. No web behavior has been added to
  `ProgramKit.Host`, and persistence technology remains consumer-owned.

## Fixed decisions

- Program Kit owns framework-neutral form, localization, action, release and compatibility
  contracts. JSON Forms, AJV, CodeMirror and Monaco are adapters, never public domain contracts.
- Form-runtime theming is CSS-first and cross-framework: semantic custom properties define branding,
  focus, shape and motion, while invalid controls retain inline errors and visible danger states.
- CodeMirror 6 is the unconditional rich JSON editor default. Monaco is a separately installed
  desktop enhancement behind the shared editor contract and must never become a transitive dependency of the default
  authoring experience. Because CodeMirror uses dynamic layout style attributes, deployments that
  prohibit all style attributes use the built-in native source editor; CSP is not weakened for an
  editor dependency. Both rich adapters insert two-space indentation for Tab by default and expose
  `Ctrl+M` as the focus-navigation toggle so the editor is not a keyboard trap.
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
actions, wizard, reusable CodeMirror editor, optional Monaco editor and the Program Kit design-system adapter. Framework adapters consume these
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

Program Kit supplies backend form/localization management contracts, validation, import/export,
review, publication, runtime and MCP capabilities. Consumers build any human administration UI in
their own design system. Program Kit does not publish a modeler or localization-management UI.

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
no unexpected page-level horizontal overflow. Critical form journeys run in each engine. Renderer
state galleries cover every published control and wizard state.

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
5. **Runtime composition**: custom controls/actions, trusted lookups and the Program Kit wizard.
6. **Localization**: backend management/runtime features, imports/exports, scopes, fallbacks,
   plural/select messages and forms integration.
7. **Operational capabilities**: resumable drafts, optional submissions/attachments, MCP/tool
   surfaces, complete in-memory reference persistence, and consumer-owned provider contracts.
8. **Release proof**: clean pack/install probes, cross-engine/device suites, security fixtures,
   upgrade/migration tests, cross-framework evidence and consumer documentation.

Each slice must pass deterministic tests and clean package-isolation probes before the next slice
relies on it. No slice may add Host-owned middleware or use `InternalsVisibleTo` for its probes.
