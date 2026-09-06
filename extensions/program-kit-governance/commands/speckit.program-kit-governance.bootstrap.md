---
description: Turn a natural project or system description into a confirmed Program Kit bootstrap intake through adaptive Q&A, a C4-aligned domain map, and change-aware re-analysis, then provide the safe one-line bootstrap command. Use for new Program Kit projects and for revisiting changed intake artifacts; do not use for ordinary feature specifications.
---

## Purpose

This skill is the Program Kit front door. The user may begin with an incomplete natural-language
description and does not need to create or name an initial-design file. Read
`references/intake-method.md` in full. Read `references/capability-index.json`, then only the
references routed by capabilities relevant to the user's description. Do not enumerate the entire
extension or ask about capability categories that are absent or explicitly excluded.
It conducts adaptive intake before the bootstrap workflow begins.

## Execution boundary

The skill may create and validate intake artifacts inside the repository. It must never run
`specify init`, Program Kit installation or update commands, or the outer
`specify workflow run program-kit-bootstrap` command. Spec Kit starts separate agent workers for
workflow command steps; an interactive agent starting the outer workflow would nest execution. On
Windows, setup from the sandbox identity can also leave generated paths with unsafe ownership.

Do not request escalation, create an approval rule, wrap the workflow command in another shell, or
start another interactive agent. This skill is guidance-only for the outer-workflow launch.
The human runs the final command from a normal user-owned PowerShell or WSL terminal in the
repository root. Stop. Do not call a shell tool to launch it.

## Entry and re-entry

On every invocation:

1. Treat `$ARGUMENTS` and the current user message as project intent, corrections, or requested
   re-analysis—not as a required path.
2. If `docs/architecture/bootstrap-intake.json` exists, run
   `python .specify/extensions/program-kit-governance/scripts/bootstrap_intake.py changes --json`.
3. If registered artifacts changed, follow the re-analysis procedure in `references/intake-method.md`.
   For a changed `workspace.dsl`, use the registered importer in `scripts/architecture_map.py` and
   write an import candidate outside the canonical paths. Never overwrite the canonical map or
   discard unsupported syntax before the user reviews the impact.
4. If no confirmed intake exists, begin from the user's description. Reflect the understood purpose,
   scope, actors, and first observable outcome before asking questions.

## Adaptive intake

Ask one to three cohesive questions per round. Incorporate each answer before selecting the next
round. Stop asking when every bootstrap-relevant uncertainty is answered, defaulted, assigned to a
human or research/design owner, excluded, or deferred to a named trigger.

For every detected need classify Program Kit coverage as `managed`, `guided`, `external`, `conflict`,
`not-declared`, or `insufficient-evidence`, then assign one allowed disposition from
`references/bootstrap-intake.schema.json`. Apply an applicable ordinary Program Kit default without
asking. Explain material acknowledgements and consequences before asking about an override. Say
"Program Kit has no declared managed capability for this need" for an unmatched need; do not claim
that Program Kit or the project cannot support it.

Keep user intent, Program Kit defaults, derived conclusions, proposals, and unresolved questions
distinct. Do not turn a suggested default into explicit user intent. Candidate vertical slices are
discovery signals only and begin with an actor or trigger and end in an observable outcome.

## Required artifacts

After the questions converge, create or update:

- `docs/architecture/project-intent.md`, including stable Q&A/evidence IDs and a compact coverage and
  disposition summary;
- `docs/architecture/architecture-map.json`, matching
  `references/architecture-map.schema.json` and containing both `system-context` and
  `domain-context` views;
- `docs/architecture/workspace.dsl`, generated from the canonical map with
  `python .specify/extensions/program-kit-governance/scripts/architecture_map.py export --map docs/architecture/architecture-map.json --format structurizr-dsl --output docs/architecture/workspace.dsl --force`; and
- a draft synthesis of `docs/architecture/bootstrap-intake.json` matching
  `references/bootstrap-intake.schema.json`.

The canonical map owns semantics. The DSL is a reviewable C4 projection and an import source. Mark
inferred bounded contexts, capabilities, ownership, and relationships `proposed` or `unresolved`;
intake does not accept architecture. Preserve the exact hash, byte count, importer ID, and importer
version for every source and bound artifact.

Present the concise synthesis and map changes to the user. Ask for confirmation only after there are
no invisible or unclassified gaps. Do not mark the intake `confirmed` from silence or inference.
After explicit confirmation, set its status to `confirmed`, refresh every artifact hash and byte
count, and run:

`python .specify/extensions/program-kit-governance/scripts/bootstrap_intake.py validate --json`

Repair validation failures and reconfirm if a repair changes meaning. Do not run bootstrap until the
contract validates.

## Required handoff

After successful validation, tell the user to run the command from a normal user-owned terminal in
the repository root. Always emit exactly one physical, fully substituted command line in its own
fenced block. Use repository-relative forward-slash paths and double-quote each `name=value`
argument. Include no placeholders, line continuations, environment variables, substitutions, shell
operators, or shell-specific syntax:

```text
specify workflow run program-kit-bootstrap --input "bootstrap_intake=docs/architecture/bootstrap-intake.json" --input "integration=auto"
```

If the user explicitly requested automatic approval and ratification, append
`--input "auto_approve_and_ratify=true"` to that same physical line. Never add this input unless the user explicitly requests automatic approval and ratification.

If preflight later reports `PROGRAM_KIT_CONCURRENT_BOOTSTRAP_RUN`, tell the user to verify whether
the listed run still has a live normal-shell workflow process. Never abandon a live run. For a stale
record, display the diagnostic's exact recovery command for the human to run; do not edit workflow
state directly.

After a workflow pause, report the run ID, review packet and named artifacts, and one fully
substituted, single-line resume command. A rejection keeps the run paused for revision and packet
regeneration; never describe rejection as approval failure or encourage approval of stale content.
