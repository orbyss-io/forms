# Tool and integration selection

Select capabilities before products. Research current options at bootstrap time because ecosystems, compatibility, maintenance, and security change.

Apply `default-adoption.md`: respect explicit intake selections and use the versioned Program Kit
profile for ordinary choices when intake is silent. Research verifies compatibility and records
exceptions; it does not reopen every explicit or default choice. Ask the human only about a genuine
exception, material acknowledgement, or consequential decision without a safe default.

For each candidate record:

- capability and risk addressed;
- fit with detected technologies and architecture;
- active maintenance, release recency, license, adoption, and exit cost;
- Spec Kit compatibility and integration mechanism;
- permissions, scripts, network behavior, and supply-chain trust;
- enforcement strength and false-positive/false-negative profile;
- lifecycle trigger, version pin, upgrade test, and removal path;
- alternatives and reasons for selection or rejection.

Community Spec Kit catalogs are discovery inputs, not endorsements. Inspect extension commands, hooks, scripts, and transitive tools. Mandatory quality controls belong in deterministic CI even when Spec Kit hooks give earlier feedback.

Evaluate rather than automatically install:

- Architecture Governance for ADR/architecture artifact gates.
- ADR tooling or a local adapter when the current ADR kit adapter is incompatible.
- API Evolve when an externally versioned contract appears.
- Reqnroll BDD for valuable multistep executable examples in .NET contexts.
- ArchUnitNET for compiled .NET dependency and layering rules.
- Structurizr DSL/C4 and arc42 when architecture-as-code and navigable documentation fit.

Program Kit's generated C4 review projection uses the optional, managed Structurizr Local profile in
`c4-viewer-tool.json`. The profile records authoritative sources, retrieval date, exact version,
license and supply-chain boundaries, update triggers, and removal path. Viewing is not a project
technology decision and does not add a bootstrap runtime dependency. Invoke
`speckit-program-kit-governance-view-c4`; never substitute Structurizr Lite or an unpinned `latest`
image.

When .NET is detected, evaluate CShells and CShells.AspNetCore when the architecture requires runtime
feature composition, per-shell or per-tenant service isolation, configuration-driven feature sets,
or dynamic activation and reload. Their presence is not a default architecture choice. Inspect the
current package maturity, supported target frameworks, abstraction/runtime package split, lifecycle,
security, routing, unload, and upgrade behavior. Pin all accepted CShells packages to one verified
version and test the composed shell graph.

Use ASP.NET Core Minimal APIs as the default built-in HTTP candidate for a .NET vertical slice when
HTTP is required. Evaluate public-schema generation and compatibility, route and operation identity,
authorization, validation, error contracts, cancellation, and OpenAPI behavior. A third-party
endpoint framework requires a separate capability gap and ADR; it is not implied by vertical slicing.

For the Program Kit .NET-to-TypeScript OpenAPI workflow, the managed exporter, oasdiff version in
`.oasdiff-version`, and isolated `openapi-typescript` default in
`.program-kit/openapi-defaults.json` are adopted baseline tools rather than candidates requiring a
new consumer ADR. Run `.program-kit/eng/openapi_init.py` for the first contract. Research is required
only for an explicit override or an additional capability the managed chain does not provide.

For modular dependency enforcement, evaluate a deterministic MSBuild/project-graph check and an
assembly architecture test such as ArchUnitNET. Prefer the smallest combination that can fail CI on
forbidden module and feature references, cycles, and unauthorized exceptions.
