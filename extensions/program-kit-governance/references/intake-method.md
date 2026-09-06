# Conversational bootstrap intake

## Outcome

Produce a user-confirmed project intent, a canonical C4-aligned architecture map, a reviewable
Structurizr DSL projection, and a validated bootstrap intake contract. Intake is complete when every
bootstrap-relevant uncertainty is answered, defaulted, assigned, or deferred; it does not require
every future product decision to be made.

## Question policy

Begin with the user's natural description. Reflect the understood intent before asking questions.
Ask one to three related questions per round and incorporate each answer before choosing the next
round. Do not run a fixed questionnaire or ask about excluded and irrelevant capability categories.

Prioritize observable value, actors, scope, trust and data boundaries, external integrations,
operational constraints, material Program Kit deviations, and the thinnest meaningful proving
journey. Apply a Program Kit default without asking when it is safe and applicable. Explain a
material acknowledgement or override before requesting a decision.

For a need with no declared Program Kit capability, say exactly that; do not claim incompatibility.
Classify it as external, research-required, or project-owned design and ask only for information the
project must supply. Defer questions that become material only at a named lifecycle trigger.

## Architecture map

The Program Kit JSON map is canonical. It preserves the portable semantics needed for C4 and
Structurizr models: static, dynamic, deployment, filtered, custom and image views; deployment
elements and instances; groups, archetypes, properties, perspectives and URLs; view filters,
ordering, layout and animation; styles, themes, terminology and branding; documentation; and
hash-bound architecture decisions. Features not yet understood by a registered importer remain
typed extensions rather than being discarded.

Its C4 System Context view contains the system in scope, people, and directly connected external
systems. Its Domain Context view adds candidate business capabilities, bounded contexts, ownership,
public contracts, data ownership, and directional relationships. Mark inferred boundaries
`proposed` or `unresolved`; intake never promotes them to Accepted architecture.

Every architecture decision records its ID, repository-relative path, SHA-256, title, date, status,
scope, owner and supersession links. Elements, relationships, views and constraints carry typed
`decision_refs`. Reject missing decisions, stale hashes, broken supersession chains, and accepted
architecture facts governed only by a non-Accepted decision. Export attached decisions with
Structurizr `!adrs` while retaining the provider-neutral canonical links.

Generate `docs/architecture/workspace.dsl` as the review projection. Treat it as importable user
input when its recorded hash changes. Import through `scripts/architecture_map.py`; never implement
ad hoc parsing inside the skill. Unsupported DSL must produce a diagnostic and leave the canonical
map unchanged. Preserve unrecognized portable statements as extensions. Classify `!script`,
`!plugin`, remote includes, remote images and remote themes as `blocked-executable`; importing or
rendering never executes or fetches them without a separate explicit policy decision and
authorization.

## Re-analysis

On every invocation, inspect the canonical artifact paths and compare their current hashes with
`docs/architecture/bootstrap-intake.json`. When nothing changed, continue the unfinished questions
or summarize the confirmed intake. When an artifact changed:

1. validate or import the changed artifact;
2. identify affected elements, relationships, capability assessments, open items, and slice signals;
3. mark only affected derived conclusions stale;
4. preserve unaffected explicit answers;
5. surface conflicts instead of choosing a winner;
6. reopen only affected questions; and
7. regenerate and reconfirm all bound artifacts.

A changed projection never silently supersedes an explicit user decision or confirmed Program Kit
default. The user must resolve the conflict.

## Completion command

After confirmation and deterministic validation, output exactly one physical command line in its own
fenced block. Use repository-relative forward-slash paths, double-quote each `name=value` argument,
fully substitute every value, and include no placeholders, backticks, backslashes, environment
variables, command substitutions, or shell-specific operators:

`specify workflow run program-kit-bootstrap --input "bootstrap_intake=docs/architecture/bootstrap-intake.json" --input "integration=auto"`

Do not run the outer workflow from an agent. Do not append automatic approval unless the user
explicitly requests it.
