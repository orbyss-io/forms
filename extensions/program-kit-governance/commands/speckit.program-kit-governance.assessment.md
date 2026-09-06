---
description: Assess a confirmed Program Kit conversational intake and create the evidence-based bootstrap decision baseline.
scripts:
  py: scripts/governance_state.py validate-installation
---

## Input

`$ARGUMENTS` identifies the deterministically validated
`docs/architecture/bootstrap-intake.json`. Read that contract first, followed by its bound
`project-intent.md` and canonical `architecture-map.json`. If any artifact is absent, unreadable,
unconfirmed, stale, or hash-inconsistent, stop and report the exact problem. The intake contract is
the sole front-door authority; do not search for or accept a legacy initial-design artifact.

## Installation preflight

Before reading the confirmed intake or writing any project artifact, run:

```text
{SCRIPT}
```

If validation fails, stop immediately and report the exact repair commands. Run those commands in the displayed order, and never continue bootstrap between them.

## Required reading

Treat the confirmed intake as the routing authority for this stage. Use its evidence IDs and bound
artifacts when a fact is ambiguous or contradictory; do not print the complete intake or map. Read
`references/default-adoption.md` and `references/capability-index.json`, then use this fixed routing map
rather than searching the references tree: languages and interfaces use
`references/software-language.md`; module, ownership, contract and domain-map boundaries use
`references/modularity-and-contracts.md`; journeys and slice signals use
`references/vertical-slicing.md`; explicit generic code-quality concerns use
`references/programming-guardrails.md`. Do not read `architecture-method.md`, `tool-selection.md`,
or `codex-desktop-windows.md` during assessment. An explicitly excluded surface is out of scope. A
language or framework name is not evidence that its technology extension is installed. Read a
technology profile only when the intake routing or installed skill guidance supplies its exact
path; otherwise treat it as absent and do not probe guessed paths, manifests, catalogs, or the
installed-extension tree. Never enumerate or bulk-read either references or installed extensions.
Read existing repository guidance and architecture artifacts only when they predate this bootstrap
and could conflict with the confirmed intake; do not overwrite user-authored work.

Apply `references/default-adoption.md`. Preserve the intake's distinction between explicit intent,
Program Kit defaults, derived conclusions, proposals, examples, and future options.
Do not reopen an explicit intake selection or an applicable Program Kit default merely because its
implementation details still need a specification. A valid question is not automatically a human
decision or bootstrap blocker.

## Work

Create or update `docs/architecture/bootstrap-assessment.md` with:

1. Purpose, actors, primary journeys, domain concepts, bounded-context candidates, module and feature candidates, external systems, data classes, trust boundaries, quality attributes, deployment assumptions, and operational constraints found in the confirmed intake and architecture map.
2. A technology inventory. Mark explicit intake choices and applicable Program Kit defaults as
   provisionally adopted by the assessment gate, with their source. Mark examples, suggestions,
   and project-specific choices outside that baseline `Proposed` unless an existing Accepted ADR
   already accepts them.
3. Contradictions, ambiguities, missing evidence, and risky assumptions with exact intake evidence IDs and architecture-map element or relationship IDs.
4. A decision backlog grouped by architecture significance. Include security, tenancy, authorization, isolation, consistency, delivery semantics, versioning, reproducibility, supply chain, observability, operability, and recovery when applicable.
5. Candidate vertical slices derived from actors, triggers, intents, commands, queries, messages, failure outcomes, and operational journeys. Mark them as discovery inputs rather than accepted decomposition.
6. A preliminary contract and ownership inventory covering public APIs, events, schemas, consumer-owned ports, provider-owned capabilities, data ownership, and suspected cross-module dependencies.
7. A traceability table from intake evidence and architecture-map identities to architecture concerns, candidate slices, and future decision tasks.

Create `docs/architecture/decision-backlog.md`. Each item must have a stable ID, question, why it matters, decision owner, dependencies, evidence needed, status, and the artifact that will close it.

Classify backlog entries as one of: resolved by explicit intake, resolved by Program Kit default,
resolved by a derived default, genuinely unresolved, or deferred until a named lifecycle trigger.
Only genuinely unresolved decisions may block an affected roadmap entry. Specification details,
acceptance criteria, and triggered production concerns are not foundation ADRs.

Create `docs/architecture/bootstrap-decisions.json` with this exact shape and the standalone
`.specify/extensions/program-kit-governance/references/bootstrap-decisions.schema.json` contract.
Do not inspect `governance_state.py` to rediscover a contract already supplied here; run its
validator after writing and use a specific diagnostic only if repair is needed.

```json
{
  "schema_version": "1.0",
  "default_profile": { "id": "program-kit-standard", "version": "<installed-version>" },
  "selected_profiles": ["dotnet", "typescript-web"],
  "dotnet": {
    "host_runtime": "ProgramKit.Host",
    "host_source": "program-kit-default",
    "program_kit_host_opt_out": false,
    "opt_out_reason": ""
  },
  "web": {
    "secure_profile": "bff-cookie-v1",
    "profile_source": "program-kit-default",
    "browser_ui": true,
    "override_reason": "",
    "threat_model": "program-kit-web-threat-model-v1",
    "security_evidence": "program-kit-web-security-evidence-v1"
  },
  "choices": [
    {
      "id": "stable-id",
      "decision": "Concise adopted choice",
      "source": "explicit-intake",
      "rationale": "Why this source applies",
      "override": "How the project can supersede it"
    }
  ],
  "overrides": [
    { "id": "stable-id", "decision": "Default replaced and chosen alternative" }
  ],
  "acknowledgements": [
    { "id": "stable-id", "summary": "Consequential fact the reviewer must understand" }
  ],
  "unresolved": [
    { "id": "stable-id", "question": "Decision only the human can safely answer", "blocks": "Affected roadmap item or gate" }
  ],
  "deferred": [
    { "id": "stable-id", "question": "Decision that is not material yet", "trigger": "Lifecycle event that makes it material" }
  ]
}
```

Allowed choice sources are `explicit-intake`, `program-kit-default`, `derived-default`, and
`override`. Use empty arrays when a category has no entries. Every object in the remaining lists
has the exact fields shown plus concise review-packet text. Unresolved and deferred entries name
the affected roadmap item or lifecycle trigger rather than becoming global blockers.

Do not guess exact toolchain versions during intake. The research stage receives the selected
profile manifests through its generated `managed_profile_pins` authority and adds the schema's
`toolchain` block from those exact values before deterministic validation.

When .NET is selected, set `ProgramKit.Host` automatically unless intake explicitly opts out. An
opt-out requires a non-empty reason and alternate host. Without an opt-out, add acknowledgement ID
`program-kit-preview-dependencies` explaining that the managed baseline uses pinned Program Kit,
CShells, and Nuplane preview packages and preview package sources; assessment approval acknowledges
this fact but does not restore packages or contact those feeds.

When a browser UI is selected, include the `web` block and set `secure_profile` to
`bff-cookie-v1` unless explicit intake requires a separately hosted browser OAuth client or records
another profile. “SPA” alone does not select direct browser authentication. `spa-pkce-v1` requires
`profile_source` `explicit-intake` or `override` and a non-empty `override_reason` describing the
deployment need and accepted browser-token consequences. Add choice ID `secure-web-profile` so the
review packet and consolidated baseline adopt the exact profile. Every authenticated browser choice
also records `threat_model` as `program-kit-web-threat-model-v1` and `security_evidence` as
`program-kit-web-security-evidence-v1`. Those IDs inherit the versioned attacker model, source-
classified decision evidence, configurable-default rationale, residual risks, verification levels,
and review triggers; do not recreate them as unresolved project questions. For a non-browser
project, set `browser_ui` to false and `secure_profile` to `none-v1`.

Do not invent acceptance outside explicit intake, the versioned Program Kit defaults, safe derived
defaults, or reviewed overrides. Record those sources as provisional baseline choices for the
assessment gate. Do not initialize application code or modify the confirmed intake, canonical
architecture map, or C4 projection during assessment. If one is wrong, stop and direct the user to
rerun the bootstrap front-door skill so the affected questions can be reopened and the artifacts
reconfirmed.

Keep the result proportional to the confirmed intake. Prefer compact tables over repeated prose,
and do not document excluded capability categories one by one. After writing, report file paths,
byte sizes, and decision counts only; do not print complete generated artifacts or repository-wide
diffs. For a single-interface, dependency-free local application, target at most 8 KiB for
`bootstrap-assessment.md` and 6 KiB for `decision-backlog.md`. Prefer one routed read batch, one
artifact-write batch, and one validation batch; expand only for a specific diagnostic.
