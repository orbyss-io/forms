# Forms and localization implementation evidence

Evidence date: 2026-09-06

## Backend boundaries

- `Orbyss.Forms.Abstractions` and `Orbyss.Localization.Abstractions` expose public semantic
  contracts without implementation dependencies.
- Forms validation, deterministic JSON Schema/JSON Forms compilation, compatibility analysis,
  editable definitions, evidence-bound review, approval, immutable releases and retirement are
  implemented behind replaceable storage ports.
- Localization supplies validation, fallback, immutable resolution, scoped messages, deterministic
  bundles and bounded CSV, JSON, XLSX, XLIFF 2.1 and PO import/export.
- Complete in-memory adapters provide deterministic non-durable testing. Filesystem adapters provide
  explicit persistence without selecting an ORM, database, migration tool or cloud provider.
- Management, runtime and submission HTTP surfaces are independent endpoint-only CShells features.
  `Orbyss.Foundation.Host` owns none of their middleware or response formats.
- One authenticated stateless MCP transport composes separate Forms operations, Forms management and
  Localization tool contributors. Tools invoke the same application services as HTTP endpoints and
  derive identity from the validated transport principal.
- Drafts, submissions, attachments, migrations, validation, compilation, imports, exports and
  lifecycle mutations retain bounded data, optimistic concurrency, idempotency and audit evidence.
- Architecture validation rejects `InternalsVisibleTo` and implementation leakage across these
  package seams.

The rejected management UI did not remove any backend capability. The deterministic validator
explicitly requires the management projects, solution membership, authoring/draft/release contracts
and both MCP catalogs.

## Frontend forms engine

The isolated `src/typescript` workspace contains twelve independently packable engine packages:

- dependency-free forms and editor contracts;
- renderer/action registry and immutable-release runtime verification;
- AJV 2020-12 build-time validation plus CSP-compatible standalone-validator generation;
- headless action, wizard and searchable-lookup controllers;
- thin React, Vue and Angular JSON Forms bindings; and
- optional application-wide semantic theme tokens.

Orbyss Forms publishes no form controls, action bars, wizard/stepper UI, searchable-select renderer,
CodeMirror adapter, Monaco adapter, component CSS, form modeler, schema modeler or localization
management UI. React, Vue and Angular bindings require the consuming application to provide its
renderer set. Editor consumers implement the dependency-free editor contract using their preferred
library.

The framework bindings share a precompiled-validator facade and translation bridge. Validation is
calculated from the start but defaults to `ValidateAndHide`; applications select
`ValidateAndShow` after their own validation-triggering action. Unknown condition keywords and
unbundled external references fail closed rather than generating browser code.

The npm v3 lock is produced and exercised with repository-managed Node 24.20.0 and npm 11.19.0.
Clean-package acceptance packs all twelve archives, installs exact framework peers into a disposable
consumer, imports every Node-loadable package and browser-bundles the Angular binding. Validation
also asserts that withdrawn component identities and their CodeMirror/Monaco dependencies are absent
from both the workspace and lockfile.

## Browser evidence

`tests/validate_forms_browser.py` builds a production React fixture with a generated standalone
validator and a deliberately minimal fixture-owned renderer. The renderer is not packed. The
Chromium/Firefox/WebKit CI matrix verifies:

- consumer renderer registration and data changes;
- neutral initial fields, application-triggered validation presentation and live error clearing;
- strict CSP without `eval`, dynamic `Function`, inline script or inline style;
- application-owned direction changes;
- automated WCAG A/AA checks for the fixture;
- touch target sizing and 320 CSS-pixel/200% text reflow; and
- same-origin operation without console or page errors.

Local Chromium and WebKit cover six desktop/phone/tablet emulation profiles. The pinned Firefox
binary cannot launch on this Windows installation (`spawn UNKNOWN` before page load), so Linux CI
remains the required Firefox engine evidence.

Because Orbyss Forms 0.9.9 publishes no visual components, the earlier physical showcase report is
not a release gate. Consuming applications own physical-device, virtual-keyboard, screen-reader,
appearance and responsive-layout acceptance for their selected renderer/design system. A future
Orbyss Forms-owned visual component must restore component-specific physical evidence.

## Deterministic suites

- `validate_forms_localization_contracts.py` covers semantic validation, deterministic compilation,
  import/export security, localization, lifecycle, compatibility and dependency isolation.
- `validate_forms_operations.py` covers governed drafts, submissions, attachments, migrations,
  endpoint composition and authenticated operational MCP tools.
- `validate_forms_management.py` covers durable authoring/release lifecycle, runtime caching,
  authenticated management endpoints and shared Forms/Localization MCP composition.
- `validate_inmemory_storage.py` covers detached state, replay, concurrency, audit, immutable writes,
  retirement and Forms/Localization parity.
- `validate_forms_frontend.py` covers all twelve package boundaries, engine behavior, thin framework
  bindings, exact tools, lockfile policy and dry-run packs.
- `validate_forms_frontend_packages.py` covers real archive installation and clean-consumer imports.
- `validate_forms_browser.py` covers the cross-engine consumer-renderer boundary described above.

No paid live bootstrap acceptance is part of this evidence unless explicitly requested under the
repository contributor policy.
