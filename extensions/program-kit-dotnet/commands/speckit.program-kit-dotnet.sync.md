---
description: Install or safely update the Program Kit managed .NET repository baseline.
scripts:
  py: scripts/dotnet_sync.py
---

## Input

`$ARGUMENTS` may contain `--check` to report drift without changing files and `--web-profile`
with `auto`, `none`, `bff-cookie`, or `spa-pkce`. The repository root is the current working directory
unless an explicit target path is supplied. `auto` reads the approved bootstrap evidence and adopts
`bff-cookie` when it detects a browser UI and no profile override.
`--persistence-profile` accepts `none` (default), `ef-postgresql`, `ef-sqlserver`, or `ef-sqlite`
only after the owning capability's persistence admission record is complete.

## Work

1. Confirm that the approved bootstrap decision register selects .NET and has not explicitly opted out
   of `ProgramKit.Host`. The hash-bound assessment approval plus Accepted bootstrap-baseline decision
   satisfy host/runtime selection and acknowledgement of the pinned preview packages and the
   `CShells Preview` and `Nuplane Preview` NuGet sources. Outside bootstrap, equivalent Accepted ADR
   and explicit acknowledgement evidence are required.
   The Program Kit-managed SDK pin remains authoritative unless that register contains the explicit
   `managed-toolchain-version` override. A different locally installed SDK is not implicit approval
   to downgrade the managed baseline.
2. For a write, run `{SCRIPT}` with `--target <repository-root> --profile-selected
   --host-runtime-accepted --preview-sources-approved`. Pass a confirmation flag only when its corresponding
   evidence exists. For a read-only drift report, pass `--check --profile-selected`; the two write approvals
   are not required because check mode changes no files.
   Pass `--web-profile spa-pkce` only when explicit intake or an Accepted ADR requires a direct
   browser OAuth client. Do not ask the user to choose merely because the UI is an SPA.
   Pass a non-`none` persistence profile only when planning resolved ownership, aggregate/transaction
   boundaries, consistency/concurrency/idempotency/isolation, migrations, authorization predicates,
   data governance, deployment constraints, and real-provider evidence from
   `references/persistence-profiles.md`.
3. Report created, updated, unchanged, and conflicted files exactly as emitted by the script.
4. Stop on conflicts. Never overwrite a consumer-modified managed file or a scaffold-once consumer file.
5. After a successful write, report that the generated `.program-kit/eng/Restore.ps1 -LockedMode` and
   `.program-kit/eng/Build.ps1 -SkipRunnableHost` access configured package sources. Do not run either command unless
   the user separately authorizes networked package restore and build verification.
6. Make clear that runtime selection is automatic for a .NET bootstrap, while applying the managed
   repository files remains a separate, reviewable synchronization action and is not a prerequisite
   for technology-neutral governance checks. Program Kit bundle updates and repository-baseline
   sync are separate operations.

The sync itself performs local, path-contained file operations and does not contact package feeds. The
generated restore wrapper confines NuGet caches, .NET CLI state, and Windows profile-based NuGet discovery
below `.program-kit/cache`; `--configfile` alone selects package settings but is not the supported hermetic
process boundary. Build, CI, release, OpenAPI, and runnable-host staging paths inherit that managed boundary
and can access the configured NuGet sources.

The ownership record is `.program-kit/managed.json`. Root MSBuild discovery extension points, application
`VERSION`, shell configuration, and `NuGet.config` are scaffolded once and remain consumer-owned. Program Kit
owns the SDK, analyzer policy, `.program-kit/eng`, container, schema, and generated workflow baselines.
For `spa-pkce`, `.program-kit/spa-pkce.json` is the scaffold-owned typed security input and
the shell-profile overlay, Keycloak realm, and browser contract are managed derived outputs. Configure
exact callback, silent-renew callback, post-logout routes, origins, scopes, renewal timeout, and
session bounds in that input, then rerun the same sync command. Wildcards, cross-origin callbacks,
contradictory lifetimes, and non-public SPA client configuration fail synchronization.
The scaffolded NuGet configuration uses nuget.org as the default public-package source while more-specific
patterns protect the approved CShells and Nuplane preview namespaces. Consumers remain authoritative over
their dependencies and may add private sources with namespace-specific mappings; they must preserve the
protected Program Kit mappings and must not map those namespaces to multiple sources.
Treat a consumer-extended configuration that passes those routing invariants as current, not as drift.
The selected secure web profile additionally owns its shell feature/configuration overlay, identity
Compose/realm fixture, web contract, and Playwright harness. `hostsettings.json` remains a clean,
scaffold-once Nuplane/host input. The BFF secret must be supplied through
`CShells__Shells__default__Configuration__ProgramKit__Web__ClientSecret`.
The identity fixture contains the bearer-only API audience plus exactly one interactive client for
the selected authenticated profile. The alternative client's registration and profile-only files
must be absent, not retained in a disabled state. `none` removes the identity fixture entirely.
