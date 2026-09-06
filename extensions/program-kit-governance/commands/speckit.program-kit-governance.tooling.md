---
description: Turn researched capabilities into a staged repository quality system.
---

## Input

`$ARGUMENTS` identifies the confirmed intake and the workflow-generated bootstrap context path.

Read the compact bootstrap stage brief first. It contains confirmed intake routing, compact
authority records, and a link to a separate hash-bound evidence index. Read the ratified
constitution in full. Do not print or read the evidence index in full; query one artifact and
heading range only when the brief lacks a fact required by a quality-system decision. Do not
bulk-read every unchanged architecture artifact or enumerate installed files.
Use `governance.paths` and `output_contract` directly; do not search `.specify`, unrelated
extensions, catalogs, or validator implementation for already supplied metadata.
Honor `output_contract.artifact_byte_budgets` after all writes and report final byte counts; do not
trade away a required control merely to reach a target.

Validate and read the ratified constitution before producing the quality system. Stop when the
constitution-ratification hash is missing or stale.

Read the approved bootstrap decision register. Treat explicit intake choices and reviewed Program
Kit or derived defaults as Accepted baseline inputs. Research may recommend a later override but
must not silently demote or replace an approved default.

## Work

Create or update `docs/architecture/quality-system.md` containing:

1. A capability matrix mapping each quality risk to prevention, static detection, test detection, runtime detection, owner, and evidence artifact.
2. A staged adoption plan: bootstrap gates, first-code gates, first-contract gates, first-deployment gates, and scale/compliance gates.
3. Exact trigger conditions for reevaluating optional tools and Spec Kit extensions.
4. A repository enforcement policy. CI is the authoritative enforcement layer once the repository
   has CI, multiple contributors, a release, or deployment. For an explicitly local,
   single-maintainer, undistributed application with no CI surface, make one deterministic local
   aggregate command authoritative and defer CI until one of those triggers occurs. Spec Kit hooks
   provide early feedback but are not the sole control.
5. Upgrade policy: pin versions, inspect release notes and scripts, exercise representative fixtures, and promote only after compatibility checks pass.
6. Dependency enforcement for the accepted bounded-context, module, feature, and contract graph. Include forbidden project/package/assembly edges, cycles, shared-store access, exception allowlists, and ownership evidence.
7. Slice-completeness evidence covering public schema compatibility, composition, authorization, observable outcomes, and architecture tests at the earliest reliable lifecycle stage.

Generic programming guardrails apply automatically. Project-specific tool selection and architecture choices remain Proposed until their ADR is accepted. Avoid duplicating capabilities already supplied effectively by the language toolchain, platform, or accepted repository tooling.

Do not manufacture a tooling ADR for standard-library test/process utilities that directly realize
an explicit automated-test requirement without adding a dependency or architecture surface. Treat
the exact installed patch within an explicitly accepted runtime minor line as remediation and
execution evidence, not as a new architecture decision. A different runtime line remains an
override and still requires the normal decision authority.

Before proposing any exact npm package graph, inspect registry package metadata for dependencies,
peer dependencies, engines, and platform constraints, and perform an isolated lockfile-only
resolution with scripts disabled. Record the exact command and result. A graph that needs
`--force`, `--legacy-peer-deps`, or ignored engine/platform constraints is not implementation-ready;
select a mutually compatible graph or isolate the generator/tool in its own explicitly governed
toolchain.

Omit control families for explicitly excluded surfaces rather than designing future gates for
them. For a single-interface, dependency-free local application, use the byte target supplied by
`output_contract`, use one
compact capability matrix, and defer future controls by lifecycle trigger without product-by-product
surveys. Report paths, sizes, and validation counts only; do not print complete artifacts or a
repository-wide diff.

For .NET, build the staged quality system around the accepted `ProgramKit.Host` default unless the
decision register contains an explicit opt-out. Keep actual repository synchronization and networked
package restore as separate, reviewable actions.

For a selected secure web profile, include the Program Kit provider-backed contract suite and its
pinned Playwright browser journey at the first-code gate. Require anonymous, wrong-role, authorized,
expiry, refresh, logout/provider-outage, antiforgery-or-CORS, security-header, readiness, correlation,
Problem Details, locale-fallback, and token-leak evidence owned by the profile. A feature adds its
meaningful policy path and outcomes; it does not select another authentication library or fixture.

Map the secure-web checks to control IDs `WEB-C01` through `WEB-C13` and assurance levels `WEB-V1`
through `WEB-V4` from `program-kit-web-security-evidence-v1`, and preserve their canonical meanings
and declared profile applicability. Do not renumber a sequential test list as `WEB-Cxx`. Give
project-specific checks a separate `WEB-Qxx` identity (or a domain-specific identity) and record an
explicit many-to-many mapping to the inherited controls. Tool output must distinguish source and
configuration checks, protocol/boundary tests, real-browser/provider tests, and deployment
assurance. A skipped real-provider, conformance, vulnerability, or risk-proportional security test
remains visible; it cannot be converted into passing evidence by a unit mock.
