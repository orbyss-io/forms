---
description: Create or update the living architecture baseline and ADR system.
scripts:
  py: scripts/governance_state.py validate
---

## Input

`$ARGUMENTS` identifies the confirmed intake and the workflow-generated bootstrap context path.

Read the compact bootstrap stage brief first. It contains the confirmed intake, canonical
architecture map, compact approved decisions and ratification records, and a link to a separate
hash-bound evidence index. Read the
ratified constitution in full. Do not print or read the evidence index in full; query one artifact
and heading range only when the brief lacks a fact required for an architecture decision. Do not
bulk-read every unchanged assessment or research artifact or enumerate installed files.
Use `governance.paths` and `output_contract` as the resolved path and validation authority. Do not
search `.specify`, unrelated extensions, catalogs, or validator implementation to rediscover them.
Honor `output_contract.artifact_byte_budgets` after all writes and report final byte counts; do not
trade away required architecture evidence merely to reach a target.

## Constitutional authority

Before reading or writing architecture, run:

```text
{SCRIPT}
```

Read the ratified `.specify/memory/constitution.md` in full. The constitution governs architecture,
ADRs, specifications, plans, tasks, implementation, and verification. Stop if the ratification
record is missing, Draft, invalid, or stale, or if the constitution contains a placeholder or TODO.

The validator confirms `.specify/governance/bootstrap-assessment-approval.json` and
`docs/architecture/bootstrap-decisions.json`. Use their compact records from the stage brief. Open
one source only if a decisive field was omitted. The hash-bound assessment gate is the human
authority for explicit intake choices, Program Kit defaults, derived defaults, disclosed
acknowledgements, and recorded overrides. Do not reopen those choices as Proposed.

## Architecture bootstrap

Preserve existing accepted decisions and user content. Honor the configured ADR and roadmap paths;
create the remaining missing artifacts under `docs/architecture/`:

- `README.md`: navigation, ownership, update rules, and status vocabulary.
- `architecture.md`: goals, constraints, context, building blocks, runtime views, deployment, cross-cutting concepts, risks, and quality scenarios.
- `quality-attributes.md`: measurable scenarios and verification methods.
- `technology-radar.md`: proposed, accepted, deprecated, and rejected technologies with ADR links.
- `traceability.md`: design -> decision -> specification -> plan -> implementation -> verification.
- `specification-roadmap.md`: created later by the roadmap command after tooling; architecture establishes
  slice identity and decision evidence, but never owns or copies roadmap-entry lifecycle status.
- `decisions/README.md` and an ADR template.

Create `decisions/bootstrap-baseline.md` as a consolidated Accepted decision recording the exact
approved decision-register hash, default-profile version, explicit choices, applied defaults,
overrides, material acknowledgements, and easy supersession path. Copy the decision-register
SHA-256 from `.specify/governance/bootstrap-assessment-approval.json`; include the stable ID of every
choice, override, and acknowledgement so validation can prove traceability. Ordinary reviewed
defaults do not need one ADR each. Project-specific choices outside that baseline remain Proposed
until their own human approval.
Write its status using the exact line `- **Status**: Accepted`. For every other ADR, use the same
field syntax with its actual lifecycle value; keep the colon outside the bold marker.

Scale the detail to the system. A one-module local process does not need speculative multi-module,
deployment, persistence, or operations prose. State a not-applicable boundary once, keep catalogs
to existing elements, and avoid inventing identifiers that do not improve traceability. For a
single-interface, dependency-free local application, use the byte target supplied by
`output_contract` for `architecture.md`.
After writing, report paths, sizes, and validation counts only; do not print complete artifacts or
repository-wide diffs.

Do not rewrite `bootstrap-assessment.md`, `decision-backlog.md`, `tooling-evaluation.md`, or
`bootstrap-decisions.json` after their approval. If one is wrong, stop and direct the user back to
the assessment review so the artifacts can be corrected, the packet regenerated, and the exact
contents approved again.

Treat `docs/architecture/architecture-map.json` as the canonical living architecture model and the
confirmed intake map as its provisional starting state. Refine it with accepted assessment choices,
the ratified constitution, and architecture evidence. Maintain its C4 System Context and Domain
Context Map as the first review views; add container, component, dynamic, deployment, filtered,
custom, or image views only when they clarify evidenced structure or behavior. Diagrams are views of
the canonical model, never independent sources of truth.

Maintain the model's first-class decision catalog. Every linked ADR records its repository-relative
path, SHA-256, title, date, lifecycle status, scope, owner, and supersession links. Add typed
`decision_refs` to governed elements, relationships, views, constraints, technology and ownership
facts. Reject missing or stale ADRs, broken supersession chains, and accepted architecture governed
only by non-Accepted decisions. Export attached ADR directories through Structurizr `!adrs` while
retaining the provider-neutral canonical links.

Preserve portable Structurizr semantics in the canonical fields and retain unknown statements as
typed extensions. Never execute `!script`, `!plugin`, remote includes, or remote image/theme fetches
during model import or export. Such features require a separate explicit policy decision and
authorization. Generate the DSL projection only through:

`python .specify/extensions/program-kit-governance/scripts/architecture_map.py export --map docs/architecture/architecture-map.json --format structurizr-dsl --output docs/architecture/workspace.dsl --force`

Then validate the canonical model with source and ADR hashes:

`python .specify/extensions/program-kit-governance/scripts/architecture_map.py validate --map docs/architecture/architecture-map.json --project-root . --verify-sources`

The architecture baseline must also define:

- the bounded-context map and ubiquitous language boundaries;
- module and feature ownership, public contracts, data ownership, and allowed dependency graph;
- Core/helper/implementation/provider/bridge/composition roles, semantic capability ownership, and
  selected runtime feature identities without layer-marker project names;
- a candidate slice catalog using the contract in `references/vertical-slicing.md`;
- the distinction between compile-time modules, runtime features, shells, and endpoints;
- shared-kernel and feature-family extension policies, including exact Accepted exceptions;
- the cross-context decision rule for bridges, events, orchestrators, and deliberate Core-to-Core
  published-language/subdomain/shared-kernel edges;
- domain-event ownership and delivery semantics, plus an explicit Integration Events/outbox gate for
  every durable post-commit, background, broker, or cross-process requirement;
- host web-runtime versus `.Api` endpoint ownership, including canonical permission identities and
  provider-claim mapping boundaries;
- proportional authorization ownership: provider mappings belong to deployment, canonical
  `permission:<identity>` policies to the selected Program Kit authentication feature, and only
  genuine resource/state/effect decisions to consumer code; a no-effect probe ends at the endpoint gate;
- how the first specification delivers an observable vertical slice rather than technical layers.

`docs/architecture/specification-roadmap.md` is the sole authority for `Candidate`, `Blocked`,
`Ready`, `Active`, `Delivered`, and `Superseded` roadmap-entry status. Before roadmap generation,
architecture and traceability may describe provisional slice identity, scope, dependencies, and
decision evidence, but must not assign a roadmap status or claim that a future roadmap record is an
authoritative current state. The deterministic post-roadmap synchronization step owns the marked
derived navigation view in both files.

## Decision policy

ADR states are `Proposed`, `Accepted`, `Rejected`, `Deprecated`, and `Superseded`. Only a human may move a project-specific ADR to `Accepted`. Every accepted technology, cross-domain dependency, public contract, data ownership rule, consistency boundary, security boundary, and material exception must cite an Accepted ADR.

Every accepted cross-module implementation reference, feature-family inheritance edge, shared store,
or runtime feature dependency must also cite an Accepted ADR and an executable or reviewable
enforcement location.

Resolve the decision backlog through focused design tasks before implementation depends on those answers. A design task produces evidence, alternatives, consequences, a proposed ADR, updated views, and follow-on specification slices. It does not implement application behavior.

Architecture documents must clearly distinguish facts confirmed by intake evidence, derived constraints, proposals, accepted decisions, and unresolved questions.

When .NET is selected without the recorded opt-out, the architecture, technology radar, and
bootstrap-baseline decision must adopt the application-neutral `ProgramKit.Host` and runnable-host release model as
Accepted. Do not scaffold or restore packages during this command.

When the decision register selects a browser UI, the architecture runtime, deployment,
cross-cutting, and verification views must adopt the exact `web.secure_profile` and reference its
versioned Program Kit contract. Do not restate its configuration and middleware decisions as open
questions. Show the same-origin BFF boundary and server-held tokens for `bff-cookie-v1`, or the
separate public client, exact CORS boundary, and browser token exposure for `spa-pkce-v1`.
The baseline and relevant views must also inherit `program-kit-web-threat-model-v1` and
`program-kit-web-security-evidence-v1` by exact ID. Record project additions and deviations in a
small security-assurance section: additional assets/threats/assumptions, overridden defaults,
accepted residual risks, owner, review condition, and verification. Do not call a working-group
draft final, a platform recommendation normative, or a Program Kit operational default
scientifically proven.
Canonical `WEB-Cxx` identifiers retain the decision text and profile applicability from the managed
evidence registry. Project-specific verification cases use another namespace, such as `WEB-Qxx`,
and map explicitly to one or more canonical controls; they never redefine a `WEB-Cxx` identifier.
