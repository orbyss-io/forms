# Changelog

## Unreleased

## 0.9.10 - 2026-09-07

- Add a hash-aware C4 viewing skill and deterministic temporary launcher for pinned Structurizr
  Local, with localhost port conflict handling, Docker/Java discovery, explicit network consent,
  cleanup, review-packet guidance, and no mutation of the canonical architecture map.
- Consolidate generated Program Kit engineering tooling under `.program-kit/eng/` and migrate
  authenticated files from the opaque top-level `eng/program-kit/` layout during managed sync.

## 0.9.9 - 2026-09-05

- Move BFF, SPA, error, and web middleware ownership into independently selectable CShell features;
  keep the application-neutral host free of authentication and response-format policy.
- Add provider-neutral client credentials, RFC 8693 token exchange, downstream API, DPoP, assurance,
  and JWKS rollover packages with deterministic public-surface probes and real Keycloak conformance.
- Prove TOTP, passkeys, recovery codes, password recovery, step-up, signing-key rotation, and custom
  branded password-reset, verification, and required-action email templates in disposable acceptance.
- Add provider-neutral identity-administration abstractions and ten opt-in Keycloak Admin REST features
  for users, applications, scopes, access, enrollment, sessions, flows, identity providers,
  organizations, and separated realm operations.
- Adopt and isolate the OpenAPI/oasdiff/NuGet workflow and expand clean-consumer verification without
  using `InternalsVisibleTo`.

## 0.9.8 - 2026-09-05

- Preflight every Spec Kit component registry, installed integration command root, current and
  release-desired managed-profile path, governance record, lock-renewal evidence path, and planned
  OpenAPI reconciliation destination before the first component mutation.
- Stop protected destination trees with stable `PKU115`, the exact blocked path, and a copyable
  outside-sandbox PowerShell retry command instead of leaking a late raw `PermissionError`.
- Prove a denied agent-owned `SKILL.md` leaves all component content unchanged and that a deliberate
  failure after bundle/workflow mutation converges idempotently when the updater is rerun.
- Validate cross-file Compose service dependencies against effective network names before startup,
  force-recreate application-side services, and verify live container network attachments afterward.
- Materialize every Keycloak client scope referenced or requested by either managed web profile and
  require clean disposable imports to complete real PAR-to-login entry for both clients.

## 0.9.7 - 2026-09-05

- Bridge verified uv-installed Spec Kit environments through the updater's executable Python when
  the Windows sandbox can read the tool but cannot launch its managed interpreter. The updater
  probes every required command before mutation and retains an exact normal-PowerShell recovery.
- Make `ProgramKitFeatureIdentity`, CLR `[ShellFeature]`, package descriptors, runtime catalog
  activation, and OpenAPI export one exact identity contract. The analyzer and host now fail closed
  instead of allowing a configured feature to disappear behind a derived CLR name.
- Correct the managed browser-persona fixture path and execute a fixture-load regression from the
  actual managed web-suite directory before Playwright.
- Split local identity frontchannel and backchannel topology without redefining container
  `localhost`: browsers retain the public Keycloak issuer while the application uses a named private
  network for discovery, token, user-info, and JWKS calls.

## 0.9.6 - 2026-09-05

- Add a managed repository-isolated restore wrapper and make build, CI/release verification, and
  lock-renewal guidance use it. The wrapper confines NuGet caches, .NET CLI state, and Windows
  profile discovery below `.program-kit/cache`, covering NuGet's ambient proxy-settings read even
  when `--configfile` is supplied.
- Normalize command-scoped Git `safe.directory` values to absolute forward-slash paths on Windows,
  retaining the empty Windows `core.excludesFile` override without changing global Git config.
- Keep exact Node/npm/oasdiff discovery outside the NuGet-isolated Windows profile, preserve valid
  toolchain evidence atomically when a renewal attempt fails, and retain a separate failure record.
- Validate runtime-closure evidence against the installed Program Kit baseline rather than the
  consumer application's independent `VERSION`, so producer-first OpenAPI works for normal
  application versions.

## 0.9.5 - 2026-09-05

- Require the exact governed .NET SDK by disabling SDK patch roll-forward in both the repository and
  generated consumer baseline. This keeps toolchain preflight, local builds, and GitHub runners on
  the same `10.0.202` SDK when newer patches are also installed.
- Make the sandbox-safe Git commit regression independent of GitHub Actions' inherited `GITHUB_SHA`,
  so it exercises the intended subprocess path consistently on Windows and Linux.

## 0.9.4 - 2026-09-05

- Compose profile-owned and consumer-owned shell configuration into one canonical effective feature
  set. Authentication, web defaults, OpenAPI, and optional Problem Details stay independently
  packaged CShell features; consumer overrides, including explicit disablement, remain authoritative.
- Make OpenAPI export reconstruct the same runtime feature graph as the host, fail on missing
  prerequisites, use the official `oasdiff` CLI contract, and isolate every NuGet and .NET cache
  used by managed build and export operations inside the repository.
- Add hash-bound, same-run runtime-closure evidence for staged packages and configuration, and
  require both runnable-host description and OpenAPI export to validate it before proceeding.
- Preflight the Specify CLI before upgrade mutation, emit exact lock-file renewal evidence when
  Program Kit NuGet pins change, and verify public NuGet propagation after publication.
- Tighten authorization ownership checks so application policy remains resource/state based while
  provider claims and canonical permission parsing stay in the packaged authentication boundary.
- Confine local test-persona credentials to the marked Keycloak fixture, generate supported
  post-logout redirect attributes, validate both realm variants against the pinned Keycloak image,
  and attach immutable host-image digest evidence to the GitHub release.

## 0.9.3 - 2026-09-05

- Preflight registered consumer-owned OpenAPI contracts before a pin-changing Program Kit upgrade.
  A stale `ProgramKit.OpenApi.Exporter` pin now stops before component mutation with `PKU110` and an
  exact contract plus specification/planning/research review list.
- Add explicit atomic producer-pin reconciliation. The opt-in updates registered contracts and exact
  planning references only after component installation succeeds, preserves an invalidation audit,
  removes stale after-tasks readiness, and returns `PKU111` with the mandatory analysis-renewal path.
- Add one deterministic implementation preflight that runs both lifecycle verification and complete
  artifact-ownership validation, preventing lifecycle-only release checks from missing `PKA014`.

## 0.9.2 - 2026-09-05

- Parse only the standardized Spec Kit findings table when completing after-tasks analysis. Severity
  labels in headings, legends, prose, and zero-valued metrics no longer create false findings.
- Persist each parsed finding as machine-readable lifecycle evidence while retaining the complete
  report and its SHA-256 binding. MEDIUM/LOW findings remain recorded and implementation-ready;
  genuine HIGH/CRITICAL rows remain blockers.
- Reject missing, duplicate, malformed, or ambiguously classified findings tables with `PKL017`.
  Evidence-format failures preserve the active analysis for a safe retry, while valid blocking
  analyses complete normally so artifact remediation starts a fresh hash-bound run.

## 0.9.1 - 2026-09-05

- Compose the local Keycloak realm from profile-neutral provider state plus exactly one selected
  interactive-client contribution. References and validators now describe BFF and SPA-PKCE as
  alternatives, and clean installs and both transition directions require the retired client to be absent.
- Require validated non-empty `iss` and `sub` claims before establishing a BFF session. The user
  projection now returns both values, and clears anomalous existing tickets with the stable
  `authentication_identity_invalid` outcome instead of emitting authenticated-plus-null.
- Add authenticated JSON-field migrations for obsolete scaffold-owned settings. Known 0.8.x root
  `ProgramKit.Web` blocks are removed atomically; customized blocks stop as zero-mutation conflicts
  with explicit migration guidance.
- Keep consumer/scaffold-owned byte changes outside Program Kit state drift, so valid edits to
  `shells.json`, `hostsettings.json`, and the OpenAPI registry leave `--check` clean while managed
  drift and unsafe migrations still fail.
- Align the runnable-host descriptor schema with the profile overlay and digest already emitted by
  its producer, and validate generated descriptors with both present and absent profile contributions.
- Add a fixed, path-safe `eng/verify.ps1` hook to managed CI and release workflows with a managed
  fallback. Consumer verification is preserved across upgrades and its failure blocks publication.
- Type-check the shipped web adapters and directly exercise the BFF logout adapter's local-path,
  antiforgery-form, popup, termination-wait, navigation, and failure-cleanup behavior.

## 0.9.0 - 2026-09-05

- Add the explicit `auto_approve_and_ratify` bootstrap input for uninterrupted development runs.
  It keeps all three review packets and hash validations, bypasses their pauses only when opted in,
  and records automatic versus interactive approval provenance in governance evidence.
- Replace the host-owned `ProgramKitWebBoundary` with independently packaged CShells features for
  BFF-cookie authentication, SPA-PKCE bearer authentication, common permission policy, web
  defaults, OpenAPI, and optional Problem Details. Profile selection now activates exactly one
  authentication feature through shell configuration, and consumers can disable the default
  exception-response feature and provide their own.
- Make .NET profile synchronization a transactional desired-state reconciliation. Plans are
  digest-bound, conflicts prevent all mutation, writes are journaled and atomic, failed applies
  roll back, interrupted transactions are recoverable, and every directed profile transition
  retires only authenticated Program Kit contributions.
- Repair upgrades affected by stale SPA-only files whose ownership disappeared from 0.8.11 state,
  while preserving modified files as explicit conflicts. Generate only the selected Keycloak
  client and render the selected profile's CShell configuration.
- Complete the BFF browser logout contract with antiforgery form and popup support, accept every
  successful 2xx permission probe while requiring an exact 403 for the wrong role, and keep the
  browser-visible error representation replaceable through `IAuthenticationErrorWriter`.
- Stage only active built-in feature packages plus a framework-compatible NuGet dependency closure;
  include the managed shell-profile overlay and its digest in runnable-host release evidence.

## 0.8.11 - 2026-09-03

- Fix constitution ratification so its multiline status substitution cannot consume the following
  blank line and `## Core Principles` heading. Finalization now preserves the reviewed bytes and
  changes only the canonical Draft status plus an initial pending ratification date.
- Validate the complete expected final constitution before atomically replacing the draft, then
  record both reviewed and expected-final SHA-256 values with the permitted substitutions.
- Cover amendment recovery by preserving the prior faulty ratification record as audit evidence
  when a corrected draft is opened and re-ratified.

## 0.8.10 - 2026-09-03

- Add a supported offline/local-release updater that locks Program Kit component mutation, invokes
  bundle, workflow, extension, and preset primitives sequentially, resynchronizes an existing .NET
  managed baseline, and refuses success until every installed version and registry converges.
- Extend installation validation to the governance preset manifest/registry, bundle preset record,
  and `.program-kit/managed.json`, preventing a newer bundle record from hiding old executable
  extension or managed-baseline content.
- Replace the unsafe two-command catalog upgrade guidance. Document the Spec Kit 1.0.4 Windows
  Codex `OPENSSL_Applink` transport failure without weakening TLS or sanitizing the agent runtime.
- Preserve immutable, hash-bound bootstrap decisions across upgrades. The local updater now writes
  Accepted, decision-hash-bound version authority to `.specify/governance/program-kit-upgrades.json`;
  governance rejects installed-version drift when that explicit evidence is absent or stale.
- Add a mandatory `after_constitution` hook that validates every new or amended constitution draft
  and regenerates its current review packet before the human ratification gate.

## 0.8.9 - 2026-09-03

- Correct `spa-pkce-v1` Keycloak generation to use configurable exact callback, silent-renew, and
  post-logout routes from the validated `.program-kit/spa-pkce.json` input. Synchronization rejects
  wildcard or cross-origin registrations and updates unchanged 0.8.8 managed output safely.
- Keep the SPA client public and secret-free throughout local composition. The SPA profile no longer
  injects the BFF client secret, and the host rejects a configured SPA client secret at startup.
- Make SPA session ownership executable: Keycloak enforces synchronized idle/maximum session bounds,
  the API validates token lifetime, and the managed browser adapter enforces `exp`, the original
  `auth_time` absolute deadline, local idle expiry, local-first logout, and token-free cross-tab sign-out.
- Disable Playwright traces, screenshots, and video for authentication evidence and validate the
  generated provider, host, browser, composition, and evidence-retention contract before launch.
- Preserve canonical `WEB-Cxx` meanings and profile applicability; project-specific checks now use a
  separate namespace and explicit many-to-many mappings instead of redefining control identifiers.
- Adopt oasdiff `1.29.1` and the isolated TypeScript generator as managed OpenAPI defaults. Add the
  empty-registry initializer, exact toolchain resolution/evidence, and repository-local installation
  of a reviewed oasdiff binary, removing the unnecessary consumer tooling ADR.

## 0.8.8 - 2026-09-03

- Replace the conventional `Domain`/`Contracts`/`Application`/`Infrastructure`/`Feature.*` topology
  with semantic `.Core`, named implementation, protocol, provider, bridge, helper, and composition
  packages. Capability contracts use domain intent rather than generic repositories/stores/units of
  work, may group naturally cohesive operations, and keep provider persistence models private.
- Correct `PKA015` so capability implementations are owned and activated by their provider/bridge
  projects. It now rejects layer-marker names, endpoint-to-provider references, forbidden role
  edges, unactivated implementations, missing Core capability paths, and exact MSBuild graph drift.
- Add `ProgramKit.DomainEvents.Abstractions` plus the default `ProgramKit.DomainEvents` CShells
  feature for awaited, scoped, sequential, bounded, observable in-process dispatch. Record durable
  Integration Events and transactional outbox semantics as an explicit blocking architecture item
  rather than overstating domain-event reliability.
- Assign generic authentication/HTTP runtime plumbing to the selected Program Kit host web profile;
  `.Api` implementations own actual endpoints, wire mappings, canonical permission requirements,
  and protocol metadata without a consumer-root `Administration.Api`/`Platform.WebBoundary` layer.
- Exercise the managed .NET 10 Microsoft Testing Platform selection against a real
  MSTest.Sdk 4.3.3 consumer solution, including the required `dotnet test --solution` invocation.
- Converge `Microsoft.Extensions.DependencyInjection.Abstractions` and
  `Microsoft.Extensions.Logging.Abstractions` to 10.0.11 through the managed central package
  baseline, preventing Testcontainers 4.14.0 graphs from introducing .NET 8 assemblies into net10
  platform and observability projects.

## 0.8.7 - 2026-09-03

- Resolve the exact managed Node and npm executables once and reuse their evidence for OpenAPI,
  web, and governance npm graphs. Managed npm execution now ignores a mismatched PATH, uses a
  writable repository cache, keeps strict TLS enabled, and supports system or explicit organization
  CA trust without insecure certificate bypasses.
- Bind managed .NET restores and local tool restores to the reviewed repository `NuGet.config` and
  repository-owned package/HTTP caches, and select Microsoft Testing Platform in both managed
  `global.json` files.
- Seed activated built-in runtime features such as `ProgramKitTasks` from their managed package pin
  even when consumer projects do not reference them directly.
- Canonicalize task checkbox state for lifecycle readiness hashes so implementation progress can be
  resumed without false `PKL012` failures; task IDs, descriptions, order, and paths remain protected.

## 0.8.6 - 2026-09-03

- Add the exact-pinned `ProgramKit.OpenApi.Exporter` tool and a managed producer-first OpenAPI
  pipeline. It composes the validated external-host feature package closure without opening a
  listener, starting consumer hosted services, or running shell initializers; materializes the raw
  ASP.NET Core document; normalizes and compatibility-checks it; runs a separately locked client
  generator; and finally compiles the consuming application's TypeScript graph.
- Replace the incomplete post-build MSBuild hook—which assumed some unspecified actor had already
  generated OpenAPI—with consumer-owned contract registration and explicit build orchestration.
  Empty registries restore no exporter or npm dependencies, while configured contracts preserve
  hash-bound producer, package, document, generator, and application evidence.
- Reject implementation readiness with `PKA014` when .NET-to-TypeScript OpenAPI plans omit the
  managed producer, staged package closure, contributing features, pinned compatibility contract,
  isolated generator graph, generated types, or application compile boundary.

## 0.8.5 - 2026-09-03

- Replace the .NET consumer package-ID allowlist with protected source routing: nuget.org accepts
  arbitrary consumer-selected public dependency graphs while the more-specific CShells and Nuplane
  namespaces remain bound to their approved preview feeds. Safely migrate unchanged managed
  `NuGet.config` files to the corrected baseline and then transfer them to consumer ownership; add a
  restore regression covering MSTest SDK, Testcontainers, ArchUnitNET, and their transitive packages.
  Sync accepts consumer-added private feeds with namespace-specific mappings while rejecting unsafe
  catch-all or protected-namespace reassignment.

## 0.8.4 - 2026-09-03

- Make paid live bootstrap acceptance entirely user-invoked. Publication no longer prompts for the
  suite or records its absence as a skip; an explicit request authorizes a single local run.
- Add a separately authorized first-slice continuation that exercises the complete installed Spec
  Kit lifecycle after bootstrap and preserves governance traceability, hook, ownership, managed-file,
  test, and exact application-behavior evidence.
- Make selected Program Kit profile manifests explicit research-stage authority and validate their
  exact pins before assessment approval. Current-version research and locally installed tools can
  no longer silently replace managed TypeScript, Node, package, or .NET SDK versions. A different
  local .NET SDK requires the recorded `managed-toolchain-version` user override; otherwise the
  generated tooling gives direct install/upgrade guidance and managed sync preserves the Kit pin.
- Accept the common bold ADR status spellings while prescribing one exact architecture-output form,
  preventing semantically Accepted bootstrap baselines from failing the final governance gate.
- Retry the disposable live catalog install only after Spec Kit explicitly reports a transient
  extension-archive transfer failure with no recorded changes.
- Reject Ready roadmap entries that hide a later Proposed decision/ADR gate, and hash-bind mandatory
  specification, plan, task, ownership, external-host, and npm-resolution contracts before
  implementation. The first-slice live fixture now keeps standard-library verification and its
  local aggregate gate inside the approved baseline instead of inventing an unapproved tooling ADR.
- Reject consumer-owned `.Host` projects and application `Program.cs` files under the default
  external `ProgramKit.Host` profile. Plans must cover feature identity, `shells.json`,
  `hostsettings.json`, validated package-closure staging, and digest-bound release evidence.
- Restrict task-path ownership checks to checkbox task records and ignore explicitly prohibited or
  comparison-only code spans, preventing explanatory references such as a feature directory,
  `Program.cs`, or `ProgramKit.Build.targets` from becoming false edit targets.
- Add strict, isolated npm lockfile resolution evidence for candidate package graphs, preventing an
  incompatible peer graph such as TypeScript 7 with `openapi-typescript` 7.13.0 from passing plan
  and task readiness or being bypassed with force/legacy-peer options.
- Re-verify approved `fnm` Node installs through `fnm exec --using=<pin>` in the same process and
  direct non-administrator Windows users to per-user manager installation rather than an
  elevation-bound Chocolatey fallback.
- Use an empty command-scoped Git excludes value on Windows live workers because Git rejects `NUL`;
  retain `/dev/null` on POSIX and never change global Git configuration.
- Separate packaged-candidate release gates from public-catalog verification, whose immutable tag
  URLs and downloadable assets necessarily become available only after publication.

## 0.8.3 - 2026-09-02

- Derive live public-install and upgrade expectations from the tagged source workflow, so
  post-publication verification cannot retain an obsolete duplicated step list when the bootstrap
  expands.

## 0.8.2 - 2026-09-02

- Normalize the initial design into a validated, provenance-bound brief before intake, then pass
  compact run-scoped stage briefs plus separate hash-indexed evidence maps between research,
  architecture, tooling, roadmap, and readiness. Fresh agents can reason from explicit routing and
  query only relevant source sections instead of rereading every unchanged artifact.
- Add an opt-in, local-only live bootstrap acceptance suite with a minimal application fixture,
  explicit paid-run approval, CI refusal, packaged-candidate installation, streamed output capture,
  workflow monitoring, retained diagnostics, advisory performance budgets, and final readiness
  validation. Windows workers retain `workspace-write`, use command-scoped Git safe-directory
  exceptions, and run Python output as UTF-8 without global Git changes or sandbox bypasses.
- Require research to preserve the reviewed decision-register item contract and self-run the
  deterministic assessment validator, preventing a semantically useful enrichment from aborting
  the workflow at the following step. Failed live reports now emphasize the causal step instead of
  cascading expected downstream-missing artifacts.
- Keep the extension catalog's advertised command count synchronized with the manifest and verify
  that relationship deterministically.
- Report per-artifact proportionality budgets as advisory live-acceptance observations alongside
  token, stream, duration, and stage-context metrics.
- Publish the decision-register schema and embed resolved configurable governance paths, intended
  writes, contract references, and validation commands in every compact stage brief so workers do
  not need repository-wide searches or validator-source inspection to discover their contract.
- Carry proportional byte budgets in stage output contracts so downstream roadmap link edits cannot
  silently push an earlier architecture artifact over its final budget. Disposable Windows workers
  also suppress inaccessible user-ignore warnings with a process- and command-scoped null exclude
  file while retaining the safe-directory fallback and unchanged global Git configuration.
- Direct initial constitution drafting to replace its scaffold in one whole-file edit, avoiding the
  recurring recoverable error caused by multiple patch operations targeting the same file.
- Give intake a fixed generic-reference routing map and forbid guessed technology-profile or
  installation-manifest probes when no exact installed profile path is supplied.
- Initially introduced a pre-publication live-suite approval prompt; the Unreleased policy above
  supersedes that behavior with explicit user-invoked execution.

## 0.8.1 - 2026-09-02

- Correct `ProgramKit.Host` to the feature-free Elsa Foundation shape: only Nuplane loading,
  the Nuplane-to-CShells assembly bridge, CShells configuration/routing, and CShells-only eager activation.
- Remove bundle/manifest parsing, package and feature policy, web/authentication/OpenAPI behavior,
  PostgreSQL access, dependency readiness, and Program Kit task contracts from the host and its image.
- Move closure validation fully into release staging. Application releases now layer staged packages plus
  `hostsettings.json` and `shells.json` onto a digest-pinned shallow host, then publish a secret-free
  `runnable-host.json` descriptor containing the resulting image repository, tag, digest, and settings.
- Teach managed synchronization to remove the obsolete bundle builder/schema only when their installed
  hashes are unchanged, preserving consumer edits as explicit conflicts.
- Withdraw 0.8.0 before adoption; its runtime publication jobs were cancelled and its GitHub release was
  returned to draft after the incorrect host boundary was identified.

## 0.8.0 - 2026-09-02

> Withdrawn before adoption. Superseded by 0.8.1 because this version incorrectly placed application,
> release, and dependency-readiness concerns in `ProgramKit.Host`.

- Make `speckit.clarify` and `speckit.analyze` mandatory ordered lifecycle hooks, preserve unrelated
  hooks across idempotent upgrades, and add resumable/reentrancy-safe hash evidence that blocks
  implementation on stale inputs or HIGH/CRITICAL findings.
- Add managed OpenAPI normalization and pinned oasdiff 1.29.1 compatibility gates through
  consumer-owned MSBuild properties, including first-baseline and approved-breaking-change flows.
- Make the real CShells `shells.json` shape authoritative for explicit feature activation, embed
  deterministic feature metadata during pack, and validate missing/duplicate/dependency/route and
  dormant-feature closure in both bundle generation and the host. Require deterministic package/main-
  assembly identity and host-private abstraction references, refresh discovery after reconciliation,
  and exercise real consumer feature initialization in a disposable host fixture.
- Add an independently hosted SPA Vite serving adapter with WEB-V1/WEB-V3 coverage for CSP, framing,
  referrer, permissions, MIME, and related policies without making local HTTP HSTS claims.
- Separate bounded Docker CLI/daemon preflight from host readiness, wait for application health in
  Compose, retain eager fail-fast shell activation, and report redacted shell, identity, and optional
  operational PostgreSQL readiness with tested degradation recovery.
- Add approval-gated exact .NET/Node toolchain remediation and separately selectable EF Core
  PostgreSQL, SQL Server, and SQLite profiles with provider-real test and governed migration rules.
- Add a machine-checkable artifact ownership/path manifest and protect managed build files by naming
  consumer-owned extension points in planning, task generation, analysis, and implementation review.
- Install an idempotent UTF-8 Python startup beside Spec Kit entry points so Windows cp1252 consoles
  can emit Unicode task templates without requiring users to discover `python -X utf8`.

## 0.7.2 - 2026-09-01

- Parse the three unique constitution metadata fields independently within the Governance section,
  retaining required order and strict value validation without depending on Markdown whitespace.
- Cover pipe-separated rows, adjacent lines, and blank-line-separated fields, including the exact
  format emitted by the affected Codex bootstrap.

## 0.7.1 - 2026-09-01

- Accept constitution version, ratification, and last-amended metadata either as the canonical
  pipe-separated row or as three adjacent Markdown lines, while preserving strict field order and
  semantic/date validation.
- Add regression coverage for the multiline constitution metadata emitted during a real Codex
  bootstrap, preventing a valid Draft from failing before its human ratification gate.

## 0.7.0 - 2026-09-01

- Add versioned `bff-cookie-v1` and `spa-pkce-v1` secure web boundary profiles, selecting the
  same-origin BFF with server-held tokens as the default for detected browser applications.
- Make the standard host own validated OIDC/bearer configuration, fallback authorization, dynamic
  role policies, server-side session tickets, antiforgery, exact CORS, security headers, correlation,
  Problem Details, localization, safe identity readiness, and protected OpenAPI generation.
- Scaffold a digest-pinned Keycloak realm with confidential BFF and public PKCE clients, normalized
  roles, deterministic user/admin/wrong-role personas, and profile-specific configuration contracts.
- Add one-command identity startup and a pinned Playwright contract harness covering real provider
  login, session refresh, local-first logout, role denial, and SPA boundary checks.
- Teach governance readiness and implementation review to treat the selected profile as bootstrap
  authority so feature specifications do not reopen platform implementation decisions.
- Add the versioned `program-kit-web-threat-model-v1` and machine-validated
  `program-kit-web-security-evidence-v1`: sources are classified by authority, every enumerated
  threat maps to controls and negative evidence, configurable defaults carry override criteria,
  residual risks and non-claims stay visible, and standards/incidents/overrides/time trigger review.
- Ship the assurance snapshot into every authenticated web scaffold and require accepted browser
  architectures to inherit its exact IDs; security-sensitive deviations require an owner, evidence,
  review condition, and regression coverage.
- Move ASP.NET Core authentication and OpenAPI packages to the 10.0.11 servicing line after package
  auditing rejected the older vulnerable OpenAPI dependency.

## 0.6.11 - 2026-09-01

- Exclude ADR support files such as `README.md` and `template.md` from Accepted and Proposed
  decision totals in the final bootstrap review packet.
- Detect an older Program Kit bootstrap run still persisted as `running` before intake, prevent
  concurrent governance mutation, and provide an explicit audited `--abandon-run` recovery for a
  hard-terminated stale record.
- Preserve abandoned workflow history by recording an `aborted` terminal state and appending a
  `workflow_abandoned` event instead of deleting or hand-editing Spec Kit run state.

## 0.6.10 - 2026-09-01

- Preserve immutable tag-catalog resolution during initial installation, then switch all four
  project catalog registrations to the trusted `main` update channel so later updates can discover
  new Program Kit versions.
- Correct the approved-bootstrap recovery procedure for consumers initialized by 0.6.9 or earlier:
  replace pinned catalog registrations before updating the workflow and bundle.
- Make the live public upgrade regression perform the catalog transition through Spec Kit's CLI,
  and assert that both Windows and Bash initializers execute the pinned-install/update-channel
  handoff.

## 0.6.9 - 2026-09-01

- Make `docs/architecture/specification-roadmap.md` the sole authority for roadmap-entry lifecycle
  status and prohibit copied status fields in architecture and traceability prose or tables.
- Synchronize marked derived roadmap views into `architecture.md` and `traceability.md`, then run a
  deterministic cross-artifact consistency validator before generating the final bootstrap review
  packet or hash-bound approval.
- Preserve blocked and unresolved roadmap entries: synchronization copies justified roadmap status
  and never promotes an entry.
- Require the readiness report to begin with the exact `**Status**: READY` line before deterministic
  completion, and add validation for completion-record hashes.
- Surface captured `complete-bootstrap` stderr through the workflow failure gate instead of losing
  the governance diagnostic behind Spec Kit 1.0.1's generic shell-exit summary.
- Add a packaged clean-consumer regression covering a legitimate Ready slice, synchronized views,
  READY reporting, successful completion evidence, and completion hash verification.
- Document safe recovery for approved 0.6.8 runs: update Program Kit, start a new workflow run over
  the existing repository, and obtain fresh review and approval rather than editing or resuming the
  persisted old workflow.

## 0.6.8 - 2026-09-01

- Make both consumer initializers fail before dependency installation or repository setup when Git
  is not initialized, and print copyable `git init` and `git status` recovery commands.
- Keep Git initialization an explicit user action while retaining the bootstrap preflight guard
  against Codex repository-check failures.

## 0.6.7 - 2026-09-01

- Require a working Git command during consumer initialization and run `git init` when the target
  directory is not already inside a work tree, preserving arbitrary existing project files.
- Reject Codex bootstrap before intake when its repository trust boundary is unavailable, with
  clean `git init` guidance instead of recommending `--skip-git-repo-check`.

## 0.6.6 - 2026-09-01

- Require an explicit Spec Kit integration ID instead of assuming Codex, let Spec Kit validate that
  integration's agent tooling, and validate executable Spec Kit and Python commands before consumer
  repository setup. Install `PyYAML>=6,<7` into the exact workflow interpreter when it is missing
  and fail early when that dependency cannot be made usable.
- Distinguish a missing PyYAML dependency from a wrong or blocked Spec Kit script flavor in the
  bootstrap preflight, with an exact repair command that does not recommend unnecessary
  reinitialization.
- Replace the nonexistent `program-kit-preflight-diagnostic` integration dispatch with a
  non-agent preflight stop, preserving the diagnostic before any intake or research work begins.

## 0.6.5 - 2026-09-01

- End both consumer initializers with a concise completion message and remove redundant
  `INITIAL_DESIGN.md` detection and bootstrap-command narration.

## 0.6.4 - 2026-09-01

- Allow the Windows and Bash initializers to run in populated repositories, including repositories
  that already have Spec Kit, while preserving unrelated project files.
- Stop before mutation when an existing or partial Program Kit installation is detected, and add
  native-platform regression coverage for both populated-repository success and repeat-install
  rejection.
- Document concrete download and execution commands for both release initializer assets.

## 0.6.3 - 2026-09-01

- Add a versioned Bash consumer initializer for Linux, macOS, and WSL alongside the Windows command
  launcher, which remains compatible with environments that enforce PowerShell `AllSigned`.
- Package, attest, checksum, document, and regression-test both initializer variants as part
  of every release.

## 0.6.2 - 2026-09-01

- Make the simulated Windows signing-policy regression self-contained on Linux release runners by
  creating its PowerShell resolver fixture explicitly.

## 0.6.1 - 2026-08-31

- Initialize Codex consumers with Spec Kit's Python script flavor and ship a copyable root command
  script as a versioned release asset.
- Validate the resolver referenced by the installed constitution skill before intake or research;
  native Windows now stops immediately when a PowerShell resolver is missing or blocked.
- Label all three human gates distinctly, rely on the mandatory constitution pre-hook exactly once,
  and strengthen draft and exact-ratification-verdict regressions.

## 0.6.0 - 2026-08-31

- Replace broad artifact prompts with concise, bounded review packets that identify every file,
  summarize explicit choices, defaults, exceptions, acknowledgements, and unresolved decisions,
  and document the revision path after rejection.
- Adopt explicit intake choices and versioned Program Kit defaults as one hash-bound bootstrap
  baseline; reserve human decisions for exceptions and consequential assumptions.
- Adopt `ProgramKit.Host` automatically for .NET unless intake records a justified explicit opt-out,
  while keeping repository synchronization and networked restore as separate actions.
- Make assessment, constitution, architecture, readiness, and completion transitions fail closed on
  missing, stale, malformed, or changed artifacts.
- Finalize constitution status and the initial ratification date deterministically from the actual
  gate result, eliminating the empty-verdict ratification loop.

## 0.5.1 - 2026-08-31

- Gate .NET baseline writes on an Accepted Program Kit host/runtime ADR and explicit preview-source approval,
  keep drift checks read-only without those approvals, and require separate authorization before networked
  restore/build verification.
- Clarify that the optional .NET runtime sync is not a prerequisite for technology-neutral governance or
  proposed quality gates.

## 0.5.0 - 2026-08-31

- Split the profile-gated .NET guidance, templates, managed-file synchronizer, and command into the dedicated `program-kit-dotnet` extension; `program-kit-governance` remains the technology-neutral governance core.
- Add `program-kit-governance-preset`, which appends architecture-governance evidence to the core feature, plan, and task templates while leaving consumer-owned template overrides highest priority.
- Make the `program-kit` bundle explicitly compose the two extensions, the preset, and the bootstrap workflow; release, catalog, installation, and upgrade checks now verify every component.
- Register constitution drafting and task-decomposition lifecycle hooks, and make the governance validator confirm the installed .NET component and bundle record before lifecycle work.
- Activate the governance configuration template with installed and local project-relative path overrides for constitution ratification, ADR discovery, and specification-roadmap validation.

## 0.4.3 - 2026-08-27

- Require humans to run Spec Kit initialization, Program Kit installation or update, and outer bootstrap orchestration from a normal user-owned PowerShell or WSL shell; Codex Desktop and interactive CLI agents stop with a copyable command instead.
- Document the Windows sandbox-identity ownership failure that can prevent later protective ACL setup, alongside the independent nested `codex exec` problem.
- Remove the escalation/approval-rule workaround and its packaged `.rules` template, and add release-asset regressions that prevent it from returning.
- Add a conservative clean-start procedure that retains `INITIAL_DESIGN.md` and preserves `.git` history unless the human explicitly chooses a new repository.

## 0.4.2 - 2026-08-27

- Define lifecycle as the model of a subject's existence and evolution, distinguish permitted trajectories from actual histories, and clarify execution path, lifetime, persistence, and API boundaries.

## 0.4.1 - 2026-08-27

The escalation-based guidance introduced by this release was withdrawn in 0.4.3 after the underlying
project-ownership failure was identified.

- Detect native Windows elevated-sandbox recursion before Program Kit asks Spec Kit to start a nested Codex CLI, and report the supported outside-sandbox boundary instead of misleading home, SQLite, or app-server errors.
- Install a Codex-facing bootstrap skill that requests escalation for only `specify workflow run program-kit-bootstrap` before the first attempt, while leaving all workflow resume gates prompted.
- Ship a narrow, reviewable Codex rules template and ordinary PowerShell fallback without changing Codex state ACLs, copying credentials, weakening the preferred sandbox, or silently installing an allow rule.

## 0.4.0 - 2026-08-26

- Publish Program Kit Host, Tasks, and Analyzers as runtime preview 0.4.0-preview.1 and add the Program Kit Host runtime for verified immutable application ZIP bundles over Nuplane and CShells.
- Add shell-lifecycle Tasks abstractions and runtime packages derived from the Elsa Foundation lifecycle pattern.
- Add Program Kit Roslyn analyzers for shell-hosted-service misuse and contextual named arguments.
- Add C# method-body, extraction, one-type-per-file, private-helper ordering, and purposeful XML documentation governance with self-enforced analyzer rules.
- Add profile-gated .NET repository scaffolding with hash-tracked managed files and conflict-safe synchronization.
- Add deterministic application-bundle creation, runtime dependency collection, layered container deployment, and CI publication workflows.
- Expand the .NET technology profile with async, synchronization, resource, LINQ, type, style, lifecycle, and deployment governance.

## 0.3.1 - 2026-08-25

- Detect version-incoherent Program Kit bundle, governance extension, workflow manifest, and workflow registry state before any bootstrap artifact read or governance-state mutation.
- Document the mandatory workflow-first upgrade sequence required by Spec Kit 1.0.1 and emit exact, integration-aware repair commands.
- Add a genuine public-style v0.2.0 to v0.3.1 upgrade regression, including the previously unsafe bundle-first path and the constitution-first workflow shape after repair.

## 0.3.0 - 2026-08-25

- Make vertical slices the default outcome-oriented delivery decomposition.
- Add bounded-context, module, feature, contract, data-ownership, and dependency governance.
- Reject peer feature implementation references by default and tightly govern feature-family inheritance exceptions.
- Expand the .NET profile with modular DDD topology, CShells abstraction/runtime boundaries, Minimal API slice contracts, and executable dependency checks.
- Make the project constitution the highest bootstrap authority with Draft/Ratified state, a dedicated human gate, and SHA-256-bound ratification evidence.
- Add the required project-level specification roadmap and block feature specifications until at least one entry is Ready without unresolved ADRs.
- Keep architecture design tasks separate from feature specification and implementation work.
- Add deterministic governance-state, package-content, workflow-order, and negative readiness tests.

## 0.2.0 - 2026-08-25

- Model Program Kit as the root product and installable bundle (`program-kit`).
- Retain Program Kit Bootstrap as the focused bootstrap workflow (`program-kit-bootstrap`).
- Rename the architecture governance extension to Program Kit Governance (`program-kit-governance`).
- Align release assets, catalogs, documentation, tests, and installed paths with the component boundaries.

## 0.1.2 - 2026-08-25

- Promote the project to the canonical `orbyss-io/program-kit` repository.
- Preserve the bootstrap bundle and workflow IDs for consumer compatibility.
- Update all catalog, release, documentation, and provenance URLs to the canonical repository.

## 0.1.1 - 2026-08-25

- Document and test the Spec Kit 1.0.1 workflow-preinstallation workaround.
- Add a live public-catalog consumer test to the release pipeline.

## 0.1.0 - 2026-08-25

- Add workflow-first repository bootstrap.
- Add architecture and implementation governance hooks.
- Add lifecycle, admission, ADR, research, and technology-profile guidance.
- Add source, packaged-install, and reproducible bundle build checks.
- Add catalog-driven installation and automated GitHub releases.
- Release under the MIT License.
