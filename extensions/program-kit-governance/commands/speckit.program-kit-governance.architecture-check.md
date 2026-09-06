---
description: Validate Spec Kit artifacts and implementation against accepted architecture.
scripts:
  py: scripts/governance_state.py validate --require-roadmap
---

## Scope discovery

Always validate the ratified constitution and roadmap:

```text
{SCRIPT}
```

This prerequisite check runs before `speckit.specify` as well as after later lifecycle steps. It
blocks every lifecycle step when the constitution is not ratified and hash-current. When invoked by
`before_specify`, add `--require-ready`; specification creation is blocked when no roadmap entry is
Ready. Before specification creation, return the prerequisite result without requiring a current
specification. Later checks accept the selected entry after its honest transition to Active and do
not require an unrelated entry to remain Ready.

For later lifecycle checks, locate the current specification, plan, tasks, or implementation from
the active Spec Kit context. Read the constitution, approved bootstrap decision register and
approval evidence, specification roadmap, architecture baseline, decision backlog, technology
radar, traceability model, and all relevant ADRs. If required artifacts are missing, fail with an
actionable bootstrap instruction.

For `after_specify`, use `scripts/lifecycle_state.py begin clarify` before clarification. If
`speckit.clarify` asks questions, leave that operation active while paused and resume it explicitly;
only complete with `questions-answered` after answers update the spec. If it asks nothing, complete
with `no-questions` and continue automatically. Do not re-enter an active operation.

For `after_tasks`, save the complete `speckit.analyze` result at
`.program-kit/evidence/after-tasks-analysis.md`, run `scripts/lifecycle_state.py begin analyze`, and
complete analysis against that report. Preserve exactly one findings table with the upstream Spec Kit
columns `ID`, `Category`, `Severity`, `Location(s)`, `Summary`, and `Recommendation`; use one row per
finding, or an empty table / a single row with placeholder identity fields and `No findings` in the
summary for a clean result. The
lifecycle parser reads only this table, persists its rows as machine-readable evidence, and ignores
severity words in headings, legends, metrics, and prose. Missing, duplicated, or malformed findings
tables fail explicitly and keep the active analysis retryable. A structurally valid report containing
HIGH or CRITICAL findings completes the run but blocks readiness, so corrected artifacts require a
fresh analysis. Then run
`scripts/artifact_ownership.py` against the feature's manifest, plan, and tasks; unknown paths,
managed-path edits, or ownership drift are errors.

For `after_plan`, and again for `after_tasks`, run `scripts/artifact_ownership.py` with the current
feature's `artifact-ownership.json` and plan (plus tasks after task generation). This deterministic
contract checks the mandatory governance sections and selected runtime profile; its `PKA010` through
`PKA012` diagnostics block the lifecycle and must not be reduced to warnings.

## Checks

- No statement conflicts with an Accepted ADR or architecture invariant.
- No statement conflicts with the ratified constitution, and no lower artifact weakens its governance.
- The work corresponds to a Ready or Active specification-roadmap entry with matching outcome, scope, ownership, contracts, lifecycle, data, quality, and dependency claims.
- Explicit intake choices, Program Kit defaults, safe derived defaults, and reviewed overrides match
  the approved bootstrap decision register and Accepted bootstrap-baseline decision.
- No Proposed technology outside that reviewed baseline is treated as accepted.
- New material choices have a Proposed ADR and are not implemented before approval.
- Domain ownership and dependency direction remain valid.
- Public APIs, events, schemas, persistence contracts, and security boundaries have compatibility and migration treatment.
- Lifecycle states, transitions, policies, terminal outcomes, admissions, retries, idempotency, and failure ownership are explicit where relevant.
- Architecture and traceability artifacts were updated when a decision changed.
- Specifications, plans, and tasks are organized around complete vertical outcomes rather than technical-layer phases.
- Every slice identifies its owner, intent, contracts, policies, effects, material failures, operational concerns, and verification in proportion to risk.
- Core/helper/implementation/provider/bridge/composition references match the accepted dependency
  graph; peer implementations and provider-private persistence are not accessed directly.
- For an external-host .NET slice, `artifact-ownership.json.runtimeComposition` identifies the
  accepted graph authorities, inventories every planned project's exact direct project/package
  references and semantic role, and assigns every capability implementation to a feature identity
  owned by and activated from the implementing project.
  Compare that inventory with both the authority artifacts and every existing `.csproj`. Inspect
  declared MSBuild references even when no CLR type currently uses them; an unused forbidden edge
  is still an architecture error. A provider or bridge with no activated capability binding blocks
  readiness. Reject endpoint-to-provider references; the external host and `shells.json` compose
  independent API and provider packages.
- Project/package names use domain language. Reject a generic `.Feature` segment and default
  `Domain`, `Contracts`, `Application`, or `Infrastructure` layer projects. A runtime feature class
  may retain the `Feature` suffix inside its named implementation package.
- Core contains stable domain semantics and capability contracts only. Reject DI/runtime feature
  registration, transport DTOs, middleware, persistence records/mappings, ORM/provider types,
  migrations, serializers, and vendor SDKs from Core.
- Capability interfaces describe cohesive domain intent. Reject generic repository/store/unit-of-work
  or CRUD surfaces and one-interface-per-method proliferation; require grouping/splitting evidence
  from consumer, consistency, security, availability, lifecycle, and replacement boundaries.
- Provider persistence records never cross provider APIs. Directly mapped domain POCOs remain valid
  only when storage concerns do not shape or escape through them.
- Cross-context collaboration follows the accepted decision rule: consumer-owned bridge for
  synchronous translation, event for independent observers, orchestrator for owned workflow state,
  or an explicitly accepted and tested Core-to-Core subdomain/published-language/shared-kernel edge.
  Require every direct Core-to-Core graph edge to have an exact `runtimeComposition.coreReferences`
  entry naming its Accepted authority and owned architecture-test evidence; reject stale entries too.
- Domain events are immutable, awaited in-process facts and never claim durable post-commit or
  cross-process delivery. Such a claim triggers the Integration Events design backlog and blocks
  implementation until its outbox/delivery contract is accepted.
- Shared abstractions, kernels, runtime feature dependencies, and feature-family extension or inheritance edges have explicit ownership and any required Accepted ADR and allowlist.
- Public endpoint, event, configuration, and schema types are distinct from domain entities and have compatibility evidence.
- Authenticated `.Api` implementations own permission/policy metadata on their actual endpoint
  groups. Reject consumer-root `Administration.Api`/`Platform.WebBoundary` packages that merely
  duplicate selected Program Kit host web plumbing.
- Reject consumer parsing of provider roles/token shapes or canonical permission claims. A
  bodyless/no-effect probe uses the managed endpoint policy only; a real protected effect also names
  and verifies its owning resource/state/effect authorization rule.
- Authenticated browser boundaries inherit `program-kit-web-threat-model-v1` and
  `program-kit-web-security-evidence-v1`; overrides identify the affected `WEB-Cxx`, `WEB-Dxx`, or
  residual-risk control, an owner, review condition, and executable evidence.
- A roadmap entry is not Ready when a required ADR is unresolved, and a design task is not presented as a feature specification or application implementation task.
- Managed `eng/program-kit/**` files are never implementation targets. OpenAPI, feature metadata,
  SPA serving security, toolchain, and persistence are configured only from their documented
  consumer-owned MSBuild, Vite, feature-adapter, or deployment extension points.
- When the selected .NET baseline has not explicitly opted out of `ProgramKit.Host`, reject every
  repository-owned host project, `.Host` source directory, application `Program.cs`, or plan/task
  that runs a custom host. Require packable feature projects with `ProgramKitFeatureIdentity`,
  an exact `[ShellFeature("<ProgramKitFeatureIdentity>")]` CLR declaration, reviewed `shells.json`
  activation, consumer `hostsettings.json`, validated package-closure staging
  through `runnable_host.py stage`, digest-bound external `ProgramKit.Host` release evidence, and
  a `PKA015`-valid runtime composition/project graph contract.
- An exact npm dependency graph is implementation-ready only with recorded registry-metadata and
  isolated lockfile-resolution evidence. Peer conflicts cannot be waived with `--force` or
  `--legacy-peer-deps`; choose compatible packages or isolate an independently governed toolchain.
  Run `scripts/npm_graph.py --package-json <candidate-package.json> --evidence
  .program-kit/evidence/npm-graph.json` before approving a plan or task set that adopts such a graph.
- An externally consumed .NET OpenAPI contract is implementation-ready only when
  `.program-kit/openapi-contracts.json` registers a complete producer-first chain. Require the exact
  managed `ProgramKit.OpenApi.Exporter` and `.oasdiff-version` pins, the validated `artifacts/runnable-host/packages`
  feature closure, side-effect-free endpoint composition, raw and normalized/baseline artifacts,
  pinned compatibility checking, an isolated generator package/lockfile, generated types, and the
  consuming application's own TypeScript compile. A plan that merely names a presumed generated
  JSON file is incomplete and must be rejected before implementation.
  `eng/program-kit/openapi_init.py` is the supported empty-registry transition; the managed defaults
  do not require another tooling ADR unless the consumer proposes an override.

Return a structured report of errors, warnings, new decisions, and required artifact updates. Errors block the lifecycle step. Never silently edit an Accepted ADR to make a conflict disappear.

When `ui-experience-v1` sources exist, run `scripts/ui_profile.py check --target .` after UI
implementation and before completion. Block generated drift, missing public/private boundaries,
unlicensed/unsafe SVG imports, duplicated metadata/route owners and unapproved analytics. Require
real consumer adapter/journey evidence in addition to the generated browser gallery. Public pages
must expose semantic content and metadata in the initial response; do not substitute client-only
head mutation or llms.txt for that contract.
