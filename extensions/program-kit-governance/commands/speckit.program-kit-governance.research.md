---
description: Research current architecture, delivery, and quality tooling for the detected context.
---

## Input

`$ARGUMENTS` identifies the confirmed intake and the workflow-generated bootstrap context path.

Read the compact bootstrap stage brief first. Its confirmed intake routing and compact authority
records define the research scope. Do not print or read the linked evidence index in full. Query one
indexed artifact and heading range only when the brief lacks a fact required for a current research
claim. Do not bulk-read every unchanged bootstrap artifact or enumerate installed files. The source
artifacts remain authoritative when the stage brief identifies missing detail or a hash mismatch.
Use the brief's `governance.paths` and `output_contract` directly. Do not search `.specify`, dump
catalogs, or inspect `governance_state.py` to rediscover paths or contracts already supplied there.
Honor `output_contract.artifact_byte_budgets` after all writes and report final byte counts; do not
trade away required evidence merely to reach a target.

## Rules

For selected `ui-experience-v1`, read its profile and `ui-evidence-v1.json`. Preserve the distinction
between standards, provider contracts, bounded empirical findings and experimental conventions.
Use the versioned layout/token/icon/metadata defaults and the isolated pinned acceptance graph;
research compatibility and deviations, not another universal frontend stack. Treat npm download
counts as a dated adoption signal, not market share or proof of design quality.

Use current research rather than memory for version-sensitive claims. Prefer official documentation, specifications, project release notes, and original research. Record source URL, publication or release date when available, access date, relevant version, maintenance signals, license, adoption cost, and trust/supply-chain considerations.

Read and preserve `docs/architecture/bootstrap-decisions.json`. Research validates explicit intake
choices and Program Kit defaults, supplies current version evidence, and records an override only
when a demonstrated incompatibility exists. It must not demote an explicit choice or default to
Proposed merely because alternatives exist.

Treat `managed_profile_pins` in the stage brief as version-selection authority. Copy its exact
`pins` into `bootstrap-decisions.json.toolchain` with source `program-kit-default` and an empty
`override_reason`. Use current research and the locally installed environment only to establish
compatibility, support status, upgrade guidance, and remediation—not to substitute a newer or older
candidate for a managed pin. If a required managed .NET SDK is not installed locally, urge the user
to install or upgrade to that exact SDK (side-by-side where supported); do not rewrite the pin to
match `dotnet --version`. Retaining a different local .NET SDK requires an explicit user decision,
source `override`, a non-empty reason, and an override record with ID
`managed-toolchain-version`. Never create a separate ADR merely to re-approve a managed pin.

Revalidate generic advice against the detected languages, frameworks, architecture style, team constraints, deployment environment, and risk. A popular tool is not automatically a suitable tool.

Research whether the proposed module and slice boundaries can be enforced with the detected build
system and language toolchain. Distinguish compile-time project or package edges, runtime activation
dependencies, public contracts, and data access. Do not treat framework-supported feature
dependencies or inheritance as evidence that a cross-feature reference is architecturally valid.

## Output

Create or update `docs/architecture/tooling-evaluation.md` with:

- problem/capability first, candidates second;
- mandatory capability versus optional accelerator;
- compatibility with the installed Spec Kit version;
- lifecycle trigger for adopting the tool;
- alternatives and rejection reasons;
- executable enforcement location (local, CI, architecture test, contract test, runtime, or manual gate);
- version pin and upgrade-validation policy;
- explicit review of workflow/extension scripts and permissions before installation.

Evaluate only capability families selected by the normalized brief or required by an accepted
boundary. Do not survey API/schema, web security, secrets, SBOM/provenance, observability,
deployment, or ecosystem-specific tools when their surfaces are explicitly excluded. Record a
single not-applicable statement for excluded families instead of researching individual products.

After research, update the decision register with verified defaults, overrides, material
acknowledgements, genuinely unresolved decisions, and deferred triggers. Validate it against the
standalone bootstrap-decisions schema named by `output_contract`. Preserve its exact item
shapes: an acknowledgement contains only `id` and `summary`; put research evidence, risk detail,
and triggers in `tooling-evaluation.md`, not extra acknowledgement fields. Preserve the exact fields
defined by intake for every other collection. Keep the human-facing decision set small. Move
implementation details into later specifications and adoption triggers rather than creating a
separate blocking ADR for every tool.

Evaluate API Evolve when the project introduces a versioned external API, event, RPC, or schema contract. Evaluate Reqnroll BDD when multistep externally observable behavior benefits from executable examples. Evaluate ArchUnitNET when .NET assembly dependency rules are present. These are evaluation triggers, not automatic acceptance.

When .NET modularity or multi-tenancy is present, evaluate CShells and CShells.AspNetCore against the
triggers and risks in the .NET technology profile. When ASP.NET Core HTTP endpoints are present,
evaluate built-in Minimal APIs and OpenAPI support before adding an endpoint framework.
For the accepted Program Kit .NET OpenAPI chain, treat the managed exporter, `.oasdiff-version`, and
isolated generator defaults as adopted; do not describe oasdiff as an unresolved candidate or create
a tooling ADR unless the project proposes an override.

For a selected .NET profile, `ProgramKit.Host` is already the Program Kit default unless intake
explicitly opted out. Evaluate compatibility and disclose the preview dependency/source risk; do
not replace that default with a conventional host merely because runtime multitenancy is absent.

Keep research proportional. For a single-language, single-interface, dependency-free local
application, target at most 8 KiB and research only the runtime plus the accepted verification
mechanism. Report sources and counts after writing; do not print the complete artifact or a
repository-wide diff.

Before reporting completion, run
`python .specify/extensions/program-kit-governance/scripts/bootstrap_context.py validate-profile-pins --run-id <workflow-run-id>`
using the run ID from the stage brief, then run
`python .specify/extensions/program-kit-governance/scripts/governance_state.py validate-assessment`.
Repair any contract error in the artifacts you changed and rerun it; do not return success while the
next deterministic workflow step is known to fail.
