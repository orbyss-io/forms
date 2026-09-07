# Program Kit .NET runtime and runnable-host releases

Program Kit's .NET profile uses independently packaged CShells features and an application-neutral
`ProgramKit.Host`. Selecting .NET adopts that host unless intake records an explicit opt-out. Installing
Program Kit alone never creates .NET files.

## The application-neutral host invariant

`ProgramKit.Host` compiles only the CShells/Nuplane runtime. Its code is limited to:

- loading standard ASP.NET Core configuration, scaffold-owned `hostsettings.json`, the managed
  `.program-kit/web-profile.shells.json` contribution, and consumer-owned `shells.json`;
- configuring Nuplane's package source and runtime loader;
- bridging Nuplane-loaded assemblies into CShells discovery;
- configuring and mapping CShells; and
- optionally triggering shell activation through `IShellRegistry`.

It does not parse a Program Kit release descriptor, inspect package or feature metadata, connect to a
database, or define feature dependency readiness. Standard authenticated web plumbing is supplied by
the host's accepted Program Kit web profile; persistence, tasks, business endpoints, and other
behavior—including authentication and HTTP defaults—arrives as packages through Nuplane and
activates through CShells.
It remains application-neutral: no business endpoint, permission identity, data provider, or
consumer feature is compiled into the host. Its modular runtime boundary is inspired by the upstream
[`Elsa.Foundation.Host`](https://github.com/elsa-workflows/elsa-foundation/tree/main/src/Apps/Elsa.Foundation.Host).

Until CShells defines a feature-health contribution contract, Program Kit does not pretend to aggregate
feature dependencies into host readiness. Container health policy belongs to the application deployment
that knows its selected features and operational dependencies.

## Repository baseline

Run `speckit.program-kit-dotnet.sync` in write mode only after Accepted evidence selects .NET,
`ProgramKit.Host`, and the disclosed preview feeds. Root `Directory.*`, `VERSION`, `shells.json`, and
`hostsettings.json` and `NuGet.config` are scaffold-once, consumer-owned files. Program Kit hash-manages
`global.json`, `.editorconfig`, generated workflows, and `.program-kit/eng`. A changed managed file is a
reported conflict, never an overwrite.

Package Source Mapping is a source-routing boundary, not a Program Kit package allowlist. The generated
`NuGet.config` routes the protected `CShells` and `Nuplane` namespaces to their approved preview feeds and
uses nuget.org as the default for other public packages. Consumers choose their direct dependencies and
may add their own private feeds with specific namespace mappings. Exact version pins, lock files,
architecture policy, vulnerability checks, and accepted decisions govern dependency selection.
Sync accepts those consumer additions when the default public route and protected namespace routes
remain intact; it reports an explicit conflict for malformed or unsafe routing.

The managed toolchain checker reads the exact SDK, Node, and npm pins, resolves their executable paths
once into `.program-kit/evidence/toolchain.json`, asks before system or network changes, installs
side-by-side where supported, and rechecks afterward. Every managed npm subprocess (OpenAPI, web tests,
and governance dependency-graph research) re-verifies and uses those exact paths rather than bare PATH
commands. npm uses `.program-kit/cache/npm`, strict TLS, and either bundled or system CA trust. Set
`PROGRAMKIT_NODE_TRUST_MODE=system` when an organization roots TLS through the OS trust store, or set
`PROGRAMKIT_NODE_EXTRA_CA_CERTS` to a reviewed PEM file; disabling strict SSL is rejected.

Managed .NET restores use `.program-kit/eng/Restore.ps1`; it selects the consumer-owned, reviewed
`NuGet.config` and confines package, HTTP, scratch, plugin, .NET CLI, and Windows profile state below
`.program-kit/cache`. `dotnet restore --configfile` selects only settings from the named file, but current
NuGet/MSBuild can still initialize proxy/user-settings infrastructure through the ambient profile. A raw
`dotnet restore --configfile` invocation therefore does not satisfy Program Kit's stronger no-ambient-read
contract. Build and repository-verification entry points establish the wrapper's environment before any
consumer-owned verification command runs. The managed `global.json` selects
`Microsoft.Testing.Platform` for .NET 10 test execution, and `Build.ps1` passes the generated solution
through the MTP-aware `dotnet test --solution` form.

The common managed package baseline centrally pins the dependency-injection and logging abstraction
packages to the same 10.0.11 servicing line used by the .NET 10 profile. A package such as
Testcontainers may request an older compatible abstraction transitively, but central transitive
pinning converges the resulting consumer graph; it does not add either abstraction to projects that
do not otherwise need it.

## Feature creation and release-time closure

The authoritative activation shape remains `CShells:Shells:<shell>:Features:<feature>`. Program Kit's
selected-profile contribution is loaded first and consumer-owned `shells.json` is loaded afterward,
so consumers can disable optional defaults or activate replacements. No shell feature is activated
merely because its package exists. A managed feature build emits
`program-kit/feature.json`; its package ID equals its assembly name and its host-supplied CShells/framework
abstractions are compile-time-private.

`.program-kit/eng/Build.ps1` restores, builds, tests, and packs the application, then stages
`artifacts/runnable-host/` for an application image. The staging directory contains the validated runtime
NuGet closure plus `hostsettings.json`, `.program-kit/web-profile.shells.json`, and `shells.json`.
Closure, duplicate version/identity, missing
dependency, inactive feature, and route-collision failures are release-pipeline concerns. The application-neutral host
does not repeat them. Activated built-in features (`ProgramKitTasks` and `ProgramKit.DomainEvents`)
are seeded from
`ProgramKit.Packages.props` even when no consumer project needs a compile-time reference to their package.
Inactive built-in feature packages are omitted, and external dependencies are resolved from the
nearest compatible NuGet framework group.

Managed CI and release workflows enter repository verification through
`.program-kit/eng/Invoke-RepositoryVerification.ps1`. If the consumer owns a regular, non-reparse
`eng/verify.ps1` inside the repository, that aggregate gate runs and any failure stops the workflow.
When it is absent, the wrapper runs the locked managed build fallback. The hook path is fixed and is
never read from arguments or environment variables; release staging remains a separate managed step.

The generated application Dockerfile derives from an approved digest-pinned `ProgramKit.Host`, copies the
staged packages into `/app/packages`, and copies the three configuration files. The generated release workflow
publishes that fully runnable image, obtains its registry digest, and emits `runnable-host.json`. That
descriptor contains only application/version provenance, image repository/tag/digest, and the exact
secret-free Nuplane/CShells configuration—including the selected profile overlay—with hashes.
`ProgramKit.Host` never consumes the descriptor.

`runnable_host.py stage` writes `.program-kit/evidence/runtime-closure.json` only after validating
the exact staged package/configuration bytes. It first marks prior evidence unsatisfied, so a failed
or interrupted restage cannot leave a usable stale manifest. Package hashes are deliberately
run-scoped: consumer `dotnet pack` ZIP timestamps can change the nupkg bytes across equivalent pack
runs. OpenAPI export and `runnable_host.py describe` therefore verify and consume the same staged
run; they do not rebuild packages between evidence and use. Reproducible consumer nupkg bytes are
welcome but are not a Program Kit correctness requirement.

Immediately after a release, a workstation may retain stale NuGet HTTP metadata and report that the
new exact version does not exist even after NuGet.org's public flat-container endpoint is ready. Do
not delete global caches. Retry the approved restore once with
`.program-kit/eng/Restore.ps1 -Subject <solution> -NoCache`; subsequent normal locked restores
may reuse the refreshed repository-confined result. The publication workflow independently waits for
every package at the public flat-container endpoint before declaring the NuGet release successful.
The checked `.program-kit/runnable-host.schema.json` declares the profile overlay and its digest as
required nullable fields, matching the producer whether an authenticated profile contribution is
staged or absent.

Managed OpenAPI verification separately remains a build concern. A consumer registers contract files in
`.program-kit/openapi-contracts.json`; an empty registry does nothing and restores no exporter or npm
dependencies. Initialize the first entry with `.program-kit/eng/openapi_init.py`; it reads the managed
exporter, oasdiff, and isolated TypeScript-generator defaults and creates the registry entry and contract
paths without requiring a tooling ADR. Each registered contract selects the managed exporter version, shell and contributing feature
identities, the validated `artifacts/runnable-host/packages` closure, raw/canonical/baseline outputs, pinned
`oasdiff`, an isolated generator package/lock/script/output, and the consuming application package/lock/type
check. The initializer creates the pinned generator `package.json` and prints the exact managed-npm command
that creates its lockfile; it never edits the application package graph. `Build.ps1` executes the completed
chain after staging and writes hash-bound evidence. Use
`-InitializeOpenApiBaseline` only for the reviewed first baseline and `-UpdateOpenApiArtifact` only for a
reviewed generated-contract revision.

`ProgramKit.OpenApi.Exporter` is packaged as a .NET local tool (a console application with the
`programkit-openapi-export` command). Consumers do not install it globally or invoke its project directly:
the synchronized local tool manifest pins it, and `openapi_pipeline.py` restores and runs that exact local
version only when at least one OpenAPI contract is registered.
The managed `.oasdiff-version` pin is `1.29.1`. `toolchain.py --include-openapi` resolves that exact
binary and records its absolute command. If it is not installed, pass a separately downloaded and
reviewed official binary to `toolchain.py --remediate --approve --include-openapi
--oasdiff-binary <path>`; Program Kit verifies its reported version and copies it into the
repository-contained `.program-kit/tools` directory. Contracts cannot select a different comparator
without a future managed-toolchain-version override/profile revision. The generator stays in its own
package and lockfile, so its TypeScript peer range does not constrain the application TypeScript graph.

## Secure web and persistence profiles

SPA serving headers remain in the Vite/static-server adapter. The SPA process itself is consumer-owned
and may be added through `Dev.ps1 -ComposeOverlay`; the managed application Compose file owns only the
API host. The accepted web profile activates separate authentication, web-defaults, OpenAPI, and
optional Problem Details CShell features through `.program-kit/web-profile.shells.json`;
consumer `.Api` packages own endpoint permission metadata and custom protocol behavior. Production
HSTS belongs to the TLS terminator.

Persistence is opt-in through `--persistence-profile`. Provider packages are context-owned named
implementations, never the host. Core projects remain free of EF/provider types, migrations are
governed deployment artifacts rather than startup behavior, and PostgreSQL/SQL Server correctness requires
provider-representative evidence.

## Upgrade note

The next sync safely replaces an unchanged Program Kit-managed `NuGet.config` with the source-routing
baseline and then transfers it to scaffold-once consumer ownership. A consumer-modified copy remains a
reported conflict. The protected `CShells` and `Nuplane` mappings must remain intact when adding sources.

The 0.8.1 sync removes the obsolete managed application-bundle schema and builder only when their recorded
installed hashes are unchanged. A consumer-modified copy is preserved as a conflict. Existing scaffold-once
`hostsettings.json` needs review because the application-neutral host no longer injects a package path; its Nuplane feed
must name `packages` (or another deployment-owned path) explicitly.

The 0.9.3 sync removes a legacy root `ProgramKit.Web` object only when its canonical value hash
matches an authenticated 0.8.x BFF or SPA baseline. A customized object is preserved as a
zero-mutation conflict so its values can be migrated explicitly to the selected shell overlay (or
typed SPA input). Consumer-owned changes elsewhere in `hostsettings.json`, `shells.json`, and the
OpenAPI registry are not Program Kit drift and do not make `--check` fail.
