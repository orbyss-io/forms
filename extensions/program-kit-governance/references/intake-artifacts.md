# Intake artifact authoring contract

Use this compact contract when the conversation has converged and the four canonical artifacts are
ready to be written. Treat the JSON schemas and Python implementations as executable contracts: do
not open them. Run the documented exporters and validators, and inspect implementation only when a
specific diagnostic cannot be resolved from this contract.

## Bootstrap intake

`bootstrap-intake.json` has exactly these top-level fields:

`schema_version`, `status`, `project`, `artifacts`, `evidence`, `facts`, `scope`, `actors`,
`journeys`, `quality_requirements`, `integrations`, `choices`, `capability_assessments`,
`open_items`, `candidate_slice_signals`, and `routing`.

- Use schema version `1.0`; status is `confirmed` only after explicit confirmation.
- `project` contains `name` and `summary`.
- `artifacts` contains `project_intent`, `architecture_map`, and `c4_projection`; each contains only
  repository-relative `path`, lowercase SHA-256 `sha256`, and integer `bytes`.
- `evidence` items contain `id`, `source`, `locator`, and `summary`. Source is `project_intent`,
  `architecture_map`, or `c4_projection`.
- Items in `facts`, every `scope` collection, `actors`, `journeys`, `quality_requirements`,
  `integrations`, and `candidate_slice_signals` contain only `id`, `statement`, and `evidence`.
- `scope` contains the arrays `included`, `excluded`, and `deferred`.
- `choices` contain `id`, `decision`, `source`, `rationale`, and `evidence`. Source is
  `explicit-intake`, `program-kit-default`, `derived-default`, or `override`.
- `capability_assessments` contain `id`, `need`, `coverage`, `program_kit_capability`,
  `disposition`, and `evidence`. Coverage is `managed`, `guided`, `external`, `conflict`,
  `not-declared`, or `insufficient-evidence`. Disposition is `explicit-user-decision`,
  `program-kit-default`, `derived-default`, `human-answer-required`, `research-required`,
  `project-owned-design`, `deferred`, or `excluded`.
- `open_items` contain `id`, `question`, `classification`, `disposition`, `blocks`, `trigger`, and
  `evidence`. Classification is `human-decision`, `research`, `project-owned-design`, or `deferred`.
- `routing` contains string arrays named `languages`, `frameworks`, `interfaces`,
  `included_surfaces`, `excluded_surfaces`, and `capabilities`.

Every evidence reference must resolve. Use empty arrays and empty allowed strings where a category
does not apply; do not invent filler records.

## Canonical architecture map

`architecture-map.json` has exactly these top-level fields:

`schema_version`, `model_id`, `title`, `sources`, `decisions`, `documentation`, `constraints`,
`elements`, `relationships`, `views`, `configuration`, and `extensions`.

Use schema version `1.0`. All IDs use lowercase letters, digits, and hyphens. Status values for map
facts are `explicit`, `derived`, `proposed`, `unresolved`, and `accepted`; intake-created domain
boundaries remain `proposed` or `unresolved`.

- Sources: `id`, `path`, `sha256`, `format`, and importer `{ "id": ..., "version": ... }`.
- Decisions: `id`, `path`, `sha256`, `title`, ISO `date`, ADR `status`, `scope`, `owner`, and
  `supersedes`. ADR status is `Proposed`, `Accepted`, `Rejected`, `Deprecated`, or `Superseded`.
- Documentation: `id`, `path`, `sha256`, and `scope`.
- Constraints: `id`, `statement`, `status`, `applies_to`, `evidence`, and `decision_refs`.
- Elements: `id`, `type`, `name`, `description`, `status`, `ownership`, `technology`, `evidence`,
  `decision_refs`, `tags`, `properties`, `perspectives`, `url`, `group`, and `archetype`.
- Relationships: `id`, `source`, `target`, `description`, `technology`, `status`, `evidence`,
  `decision_refs`, `tags`, `properties`, `perspectives`, and `url`.
- Views: `key`, `type`, `title`, `description`, `scope`, `elements`, `relationships`,
  `decision_refs`, `filters`, `order`, `layout`, `animations`, and `properties`.
- Configuration: `styles`, `themes`, `terminology`, `branding`, and `properties`.
- Extensions: `id`, `kind`, `content`, `policy`, and `source`; policy is `preserve`,
  `blocked-executable`, or `approved-external`.

Element types are `person`, `software-system`, `external-system`, `container`, `component`,
`domain-capability`, `bounded-context`, `data-store`, `deployment-node`, `infrastructure-node`,
`software-system-instance`, and `container-instance`. View types are `system-context`,
`system-landscape`, `container`, `component`, `domain-context`, `dynamic`, `deployment`, `filtered`,
`custom`, and `image`. Perspectives contain `name`, `description`, and `value`.

Include at least the required `system-context` and `domain-context` views. Use empty collections and
strings for required fields that do not apply. Do not add containers, deployment nodes, integrations,
or decisions without intake evidence.

## Write and validate

Write the intent and both JSON documents in one focused edit batch. Then:

1. Export `workspace.dsl` through the exact command in the front-door skill.
2. Refresh all three artifact hashes and byte counts in the draft intake.
3. Validate the map, then validate the intake through the exact commands in the front-door skill.

Use validator diagnostics for a targeted repair. Do not print whole artifacts, schemas,
implementations, or repository-wide diffs during verification.
