# Architecture method

## Artifact hierarchy

1. Project constitution: highest ratified governance authority and amendment policy.
2. Confirmed bootstrap intake: user intent, classified gaps, and starting assumptions interpreted under the constitution.
3. Canonical architecture map and architecture baseline: the current coherent model, views, constraints, quality scenarios, risks, and ADR links.
4. ADRs: history and authority for significant project-specific choices.
5. Specification roadmap: governed portfolio of candidate feature specifications.
6. Feature specifications: implementable vertical behavior slices constrained by the earlier authority.
7. Plans and tasks: delivery design and work decomposition.
8. Implementation and verification evidence.

Later artifacts cannot silently contradict earlier accepted authority. When a valid new insight changes architecture, propose an ADR, obtain human acceptance, update the baseline and traceability, then continue the Spec Kit flow.

The constitution is not an ordinary feature specification and never enters the feature
specification/plan/task/implement lifecycle. Drafting revokes stale ratification evidence. Only a
dedicated human gate followed by hash-bound validation makes the constitution authoritative.

The specification roadmap is also not an implementable specification. It owns sequencing and
readiness of candidate specifications. A roadmap entry cannot become Ready while a required ADR is
unresolved.

## Design tasks before feature slices

Architecture gaps are resolved as focused design tasks. Each task frames one decision, gathers evidence, compares credible alternatives, records consequences, updates views, and identifies which specifications it enables. Examples include isolation boundaries, queue/outbox semantics, tenancy and authorization, contract versioning, package security, reproducibility, signing/provenance, and recovery.

Design tasks do not pass through `speckit.implement` as application work. They update evidence,
Proposed ADRs, architecture views, traceability, and the roadmap entries they unblock.

## Outcome-oriented decomposition

Use `vertical-slicing.md` as the default delivery method and `modularity-and-contracts.md` for
ownership and dependency boundaries. Candidate slices begin with an actor, trigger, or intent and
end in an observable, verified outcome. Technical layers may exist inside a module, but they are not
the primary specification or delivery units.

The architecture baseline records bounded contexts, modules, features, slices, contract owners, data
owners, and allowed dependency edges. A slice may cross internal technical concerns without crossing
those ownership boundaries invisibly.

## Status discipline

Use `default-adoption.md` during bootstrap. Explicit intake choices, applicable Program Kit
defaults, and safe derived defaults are adopted together by the hash-bound assessment gate and
recorded in the Accepted bootstrap-baseline decision. An ordinary default does not require a
separate approval ceremony.

Choices outside that reviewed baseline begin `Proposed`. Only an Accepted ADR promotes those
project-specific choices to `Accepted`. Rejected, Deprecated, and Superseded items retain links to
the decision history.

## Living architecture

Architecture changes in the same change set as the decision or implementation that invalidates it. CI checks machine-verifiable structure and traceability; human review owns architectural judgment.
