# Forms implementation plan

Status: approved on 2026-09-06. This plan does not authorize publication or remote operations.

Frontend publication is fixed to GitHub Packages under `@orbyss-io`; the workflow will be enabled only
after the package set is complete. See `docs/frontend-package-publication.md`.

## Physical-review decision

The forms engine was accepted. The TypeScript form-modeler, schema-modeler,
localization-management and Orbyss Forms-authored form-component packages were removed from the
publishable family after physical review. Orbyss Forms retains the backend contracts, validation,
management APIs, storage ports, MCP operations and headless frontend engine; it ships no management
UI or form renderer components. This decision supersedes historical UI progress notes below.

## Implementation progress

As of 2026-09-06:

- Slice 1 is implemented in the generated browser harness for Chromium, WebKit, phone, tablet,
  desktop, orientation, touch, reflow, RTL and theme coverage. Local Firefox launch remains blocked
  before page load by the Playwright 1.62.1 Windows bundle activation defect recorded in
  `docs/ui-experience-evidence.md`; CI retains the Firefox requirement.
- Slice 2 is complete: independent Forms semantic contracts, lifecycle, concurrency, idempotency,
  audit, wizard, icon, action and runtime ports compile with no implementation dependencies. The
  optional Forms/Localization bridge consumes the separately released Localization abstractions.
- Slice 3 is implemented through provider-neutral validation, deterministic JSON Schema/JSON Forms
  UI Schema compilation, renderer/action/translation manifests, compatibility analysis, and atomic
  digest-verified immutable filesystem release stores. AJV 2020-12 parity and hostile runtime
  artifact fixtures now exist in the isolated frontend workspace. Compiler-generated fixture
  exchange and bundled-helper browser acceptance remain part of the release-proof slice.
- Slice 4 provides JSON-safe runtime contracts, release-integrity and schema-bound checks, a
  renderer/action registry, AJV build-time standalone compilation, a dependency-free editor
  contract and thin React/Vue/Angular JSON Forms bindings over the precompiled-validator facade.
  Applications supply all renderer components, editor implementations and CSS. A compiler-emitted
  .NET release fixture is consumed byte-for-byte by the TypeScript integrity/runtime path.
- Slice 5 retains only headless capabilities: the portable wizard parser/state machine,
  manifest-backed action controller and trusted searchable-lookup controller. Orbyss Forms publishes
  no wizard, action-bar, lookup or core-control renderer.
- Slice 6 moved the Localization implementation, formats, storage and management surfaces to the
  independent Localization repository. Forms retains only its explicit translation-manifest bridge
  to `Orbyss.Localization.Abstractions`.
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
  transport composes independently selected Forms contributors without Host behavior. Consumers
  may independently select the Localization contributor in their application composition root.
  Complete bounded in-memory adapters drive the Forms public-contract, management HTTP, runtime,
  and MCP probes.
- Slice 8 includes package-isolation architecture checks, shell-portable frontend tests, real
  tarball inspection, a disposable consumer of all twelve engine packages, and read-only
  Chromium/Firefox/WebKit CI using a fixture-owned renderer. Orbyss Forms-owned UI prototypes were
  removed. No web behavior has been added to `Orbyss.Foundation.Host`, and persistence technology remains
  consumer-owned.

## Fixed decisions

- Orbyss Forms owns framework-neutral form, action, release and compatibility
  contracts. JSON Forms and AJV remain adapter boundaries; renderer libraries and editors are
  consumer choices.
- The optional `ui-theme` package contains application-wide semantic tokens only. It is not a
  component stylesheet.
- `forms-editor-contracts` specifies safe mounting, diagnostics and keyboard behavior without
  selecting CodeMirror, Monaco or another editor.
- Orbyss Forms tests its engine through fixture-owned renderers on Chromium, Firefox and WebKit.
  Physical layout, touch, screen-reader and appearance acceptance belongs to the consuming
  application and its selected renderer/design system.
- Management and runtime boundaries are separate CShells features. The Host does not register form,
  submission, editor or action middleware/endpoints.
- In-memory persistence is the deterministic test/development reference. It is never represented as
  durable. Filesystem persistence is an explicit adapter. Orbyss Forms does not select a production
  database, ORM, migration system, or object-storage provider for consumers.
- Every mutation uses optimistic concurrency, an idempotency key and audit metadata. Published form
  releases are immutable.
- Server-side validation and authorization remain authoritative. Schemas, UI schemas, translations,
  renderer options and actions are data; none may carry scripts, arbitrary callbacks or executable
  markup.

## Package topology

The .NET boundary is split into:

- `Orbyss.Forms.Abstractions`: identifiers, authoring commands, immutable release contracts,
  diagnostics, compatibility manifests and narrow query ports.
- `Orbyss.Forms.Core`: validation and release compatibility analysis.
- `Orbyss.Forms.Application`: authoring, deterministic compilation, evidence-bound review,
  publication, bounded queries and retirement orchestration over replaceable stores.
- `Orbyss.Forms.JsonForms`: compilation to JSON Schema/JSON Forms UI Schema, AJV parity fixtures
  and translation-requirement extraction.
- `Orbyss.Forms.Storage.Abstractions`, `.InMemory` and `.FileSystem`: narrow consumer-owned
  persistence ports, a complete non-durable test/development reference, and an explicit filesystem
  adapter without leaking persistence models into application contracts.
- `Orbyss.Forms.Web.Management` and `.Web.Runtime`: independently selected CShells features.
- `Orbyss.Forms.Submissions`: optional drafts, resumability, attachments and submission
  lifecycle, including compatibility-aware migration through explicitly registered trusted
  handlers; form rendering does not imply data collection.
- `Orbyss.Foundation.Mcp.AspNetCore`: the single protected stateless Streamable HTTP transport, without
  domain tools or middleware ownership.
- `Orbyss.Forms.Mcp.AspNetCore`, `.Tool`, `.Management.Mcp.AspNetCore` and `.Management.Tool`:
  independently selected tool contributors over the same application services, without a second
  rules engine or independently mapped MCP endpoints.
- `Orbyss.Forms.Localization`: the optional bridge from compiled Forms translation requirements to
  the independent `Orbyss.Localization.Abstractions` contract package. Localization implementations,
  formats, storage and management features remain outside this repository.

Frontend packages mirror those seams: contracts, JSON Forms runtime integration, renderer registry,
governed actions, wizard state, lookups, editor contracts, semantic theme tokens and thin framework
bindings. Business applications supply renderers and do not import management-plane internals.

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

The independent Localization bounded context owns locales, structured scopes, messages, context,
placeholders, provenance, workflow state and fallback policy. Forms emit translation-requirement
manifest entries and reference stable keys; they do not own translation values. The optional bridge
maps those requirements through dependency-free Localization contracts.

Messages preserve typed arguments and plural/select behavior behind an adapter compatible with
Unicode/CLDR semantics. Locale identifiers use BCP 47. Language and direction metadata travel
together. Source/default text keeps a form usable when localization is not installed, while a
consumer may make locale completeness a publication policy.

## Consumer-owned rendering contracts

Orbyss Forms retains a framework-neutral wizard state machine for current, visited, completed,
warning, error, skipped, optional and disabled states; linear, non-linear and visited-only
navigation; validation gates; conditional steps; and resumable progress. It does not render that
state. Applications map it to their selected stepper or design-system component.

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
Applications implement the combobox or other visual control and consume only the headless lookup
state. Dependent filters are read only from declared rooted data JSON Pointers.

## Authoring and localization integration

Orbyss Forms supplies backend form management contracts, validation, review, publication, runtime
and MCP capabilities. Consumers build any human administration UI in their own design system.
Localization management and import/export capabilities come from the independent Localization
package family.

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

## Engine quality matrix

Core CI exercises the bindings through fixture-owned renderers in Chromium, Firefox and WebKit.
It verifies precompiled validation, hidden-to-visible validation-mode transitions, data changes,
translation integration, strict CSP and dependency isolation. The fixture is evidence for the
engine boundary only; it is not a published component or a substitute for acceptance of the
consumer's selected UI library.

## Delivery slices

1. **UI contract hardening**: make the multi-device matrix normative and extend the generated UI
   acceptance harness beyond Chromium-only narrow-viewport approximation.
2. **Contracts**: canonical form models, commands, queries, diagnostics, lifecycle,
   concurrency/idempotency/audit contracts and architecture tests.
3. **Compiler and storage**: JSON Forms compilation, translation manifests, compatibility analysis,
   immutable file-system stores and deterministic fixtures.
4. **Runtime**: JSON Forms runtime adapter, renderer registry, editor contract and thin framework
   bindings requiring application-supplied renderers.
5. **Runtime composition**: headless actions, trusted lookups and wizard state.
6. **Localization integration**: an optional bridge from Forms translation requirements to the
   independently released Localization abstractions.
7. **Operational capabilities**: resumable drafts, optional submissions/attachments, MCP/tool
   surfaces, complete in-memory reference persistence, and consumer-owned provider contracts.
8. **Release proof**: clean pack/install probes, cross-engine/device suites, security fixtures,
   upgrade/migration tests, cross-framework evidence and consumer documentation.

Each slice must pass deterministic tests and clean package-isolation probes before the next slice
relies on it. No slice may add Host-owned middleware or use `InternalsVisibleTo` for its probes.
