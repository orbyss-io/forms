# Program Kit architecture

## Purpose

This project owns the reusable method for turning a user's initial description and adaptive intake answers into a governed Spec Kit repository. It does not own any consuming application's architecture.

## Components

| Component | Responsibility |
|---|---|
| Workflow | Orders bootstrap activities and approval gates, with explicit opt-in automatic routing for uninterrupted development runs. |
| Extension commands | Give agents deterministic responsibilities and output contracts. |
| Extension hooks | Make architecture validation part of the normal Spec Kit lifecycle. |
| References | Define generic policies and technology-triggered guardrails. |
| Bundle | Pins and distributes the tested component set. |
| Test harness | Validates source manifests and builds a reproducible artifact. |
| Governance-state validator | Revokes stale constitution authority, hash-binds human ratification, and validates specification-roadmap readiness. |

## Dependency direction

The workflow depends on command IDs exposed by the extension and one core Spec Kit command. Commands
depend on reference documents and the fixed-path governance-state validator, but references do not
depend on Spec Kit runtime behavior. The bundle composes components and adds no behavior.

The bootstrap invokes Spec Kit's core constitution command as the canonical writer. Program Kit owns
the surrounding Draft/Ratified state machine, dedicated human gate, exact-content hash, and readiness
checks because the core command does not itself represent human ratification. The ratified
constitution governs architecture, ADRs, the specification roadmap, feature specifications, plans,
tasks, implementation, and verification.

Bootstrap uses a source-aware default-adoption model. Explicit intake choices, versioned Program Kit
defaults, safe derived defaults, and reviewed overrides are approved as one hash-bound assessment
baseline. Ordinary defaults do not create repeated human decision chores. Genuinely unresolved and
triggered future decisions remain scoped to the lifecycle work they materially affect.

Interactive approval remains the default. The `auto_approve_and_ratify` workflow input is a single,
explicit opt-in that routes assessment approval, constitution ratification, and final bootstrap
approval through their fixed deterministic verdicts. Every review packet is generated and
hash-validated before its automatic transition, and governance evidence records whether the
transition was interactive or automatic so a completed development bootstrap remains reviewable.

Vertical slices are the default delivery unit. Domain-specific Core packages own stable semantics
and cohesive capability contracts. Domain-named, protocol, provider, bridge, helper, and composition
packages implement them; features are runtime identities and activation types rather than project
layers. Shells are runtime isolation contexts and endpoints are transport adapters. Provider-private
persistence never becomes a cross-context model. The generic method defines these boundaries while
technology profiles map them to language and framework mechanisms.

Program Kit supplies lightweight abstractions and a default non-durable in-process dispatcher for
domain events. Durable post-commit or cross-process delivery is a separately governed Integration
Events concern and is blocked on the architecture backlog before first use.

Third-party extensions are evaluated by the workflow and recorded in the consuming project's tooling decision record. They are not dependencies of this source project unless a later ADR accepts them as universally required.

## Trust boundary

Workflow prompts and initial-design content are untrusted inputs. They never flow directly into a
workflow shell step. Hooks invoke agent commands whose instructions require explicit approval for
destructive or externally publishing actions. The packaged Python governance-state validator accepts
only fixed project-relative paths and a literal ratification verdict; it does not execute user input,
network calls, or external processes.
