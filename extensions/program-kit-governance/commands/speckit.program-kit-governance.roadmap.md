---
description: Create the governed project-level portfolio of candidate feature specifications.
scripts:
  py: scripts/governance_state.py
---

## Preconditions

`$ARGUMENTS` identifies the confirmed intake and the workflow-generated bootstrap context path.
Read the compact bootstrap stage brief first. It contains confirmed journeys, candidate slice
signals, the canonical architecture map, and compact ratified
authority records, and a link to a separate hash-bound evidence index. Read the ratified
constitution in full. Do not print or read the evidence index in full; query one artifact and
heading range only when the brief lacks a fact required to define an entry. Do not bulk-read every
unchanged bootstrap artifact, search other artifact directories, or enumerate installed files.
Use `governance.paths` and the exact writes and validation command in `output_contract`. The roadmap
field contract is stated below. Do not search `.specify` or inspect `governance_state.py` to
rediscover either contract; run the supplied validator and respond only to a specific diagnostic.
Honor `output_contract.artifact_byte_budgets` after every write, including edits to existing files.

Validate the ratified constitution before doing any work:

```text
{SCRIPT} validate
```

Use the validated context to cover the architecture baseline, ADRs, decision backlog, tooling
evaluation, quality system, traceability model, and candidate vertical slices. Stop if ratification
is missing or stale.

Use the compact approved decision and Accepted baseline records from the stage brief. Open a source
only for a decisive field omitted from that projection. Explicit intake choices and adopted Program
Kit defaults do not appear as unresolved ADR prerequisites.
Genuinely unresolved decisions block only the roadmap entries they materially affect. Deferred
production, scale, retention, recovery, or long-running-operation choices do not block an unrelated
first vertical slice before their named trigger.

## Output

Create or update `docs/architecture/specification-roadmap.md`. This is a portfolio—the specification
of candidate specifications—not an implementable feature specification and never an input to
`speckit.implement`.

This file is the sole authoritative source for roadmap-entry lifecycle status. After writing it,
update `docs/architecture/architecture.md` and `docs/architecture/traceability.md` so they contain no
copied status fields or tables for roadmap entries and no stale claims that a roadmap record does not
yet exist. Preserve their design, decision, ownership, and verification traceability. Do not write or
edit the marked `PROGRAM-KIT:ROADMAP-VIEW` section; the deterministic synchronization step owns it.
Make the smallest link-only edits needed outside the new roadmap, do not restate roadmap fields, and
check the final byte count of each edited file against `output_contract.artifact_byte_budgets`.

For each record use the heading `### <ID>: <Title>` and include exactly these list-item forms, with
the colon outside the bold label (for example `- **User-visible outcome**: ...`):

- **User-visible outcome**
- **Scope**
- **Non-goals**
- **Required Accepted ADRs**
- **Dependencies**
- **Owned public contracts**
- **Owned lifecycle portions**
- **Owned data**
- **Quality scenarios**
- **Verification responsibility**
- **Recommended sequence**
- **Status**

Statuses are `Candidate`, `Blocked`, `Ready`, `Active`, `Delivered`, and `Superseded`. Bootstrap may
create Candidate, Blocked, and Ready records. A record is Ready only when every required ADR is
Accepted, its dependencies and ownership are explicit, and the feature can proceed through
planning and implementation without a hidden decision or approval prerequisite. Put every required
ADR in `Required Accepted ADRs`; never hide a later implementation blocker in Dependencies,
Verification responsibility, or Recommended sequence while marking the record Ready.

Design tasks remain separate. They produce evidence, alternatives, Proposed ADRs, updated views, and
unlocked roadmap entries; they are not feature specifications or application implementation work.

After writing the roadmap, run:

```text
{SCRIPT} validate-roadmap
```

Do not promote a record merely to make bootstrap pass. Keep a record `Candidate` or `Blocked` when
its required ADR, dependency, ownership, contract, lifecycle, data, quality, or verification evidence
is unresolved. The later synchronization step only copies the status already justified here; it
never chooses or promotes a status.

Report blocked records and the exact design task or ADR that can unlock each one.

Start with one roadmap entry per normalized user-visible journey unless accepted architecture
requires a split. Reuse the compact authority and normalized brief rather than reconstructing the
design from every downstream document. Report entry IDs, statuses, final byte counts, and validation
counts only; do
not print the complete roadmap or repository-wide diffs.

For `ui-experience-v1`, the first slice renders the consumer's brand, layout and a real user outcome.
Login/logout supports that journey when needed; inherited authentication correctness is Program Kit
contract evidence, not a substitute first product slice. Include page intent and initial metadata
where public discovery matters, and verify the accepted framework adapter against the UI contract.

For authorization journeys, distinguish a bodyless/no-effect access probe from a protected business
effect. The former is Ready with managed endpoint `permission:<identity>` policy evidence and must
not invent an inner service; the latter also owns a resource/state/effect authorization rule.
