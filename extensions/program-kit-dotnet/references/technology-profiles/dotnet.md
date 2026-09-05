# .NET profile

Persistence is separately admitted through `../persistence-profiles.md`; no provider is selected by
this general .NET profile or by an operational database health probe.

## Baseline

When .NET is detected, evaluate and normally enforce:

- a current supported SDK/runtime policy pinned in `global.json` where appropriate;
- nullable reference types enabled;
- compiler warnings and selected Roslyn/.NET analyzers treated as errors in CI;
- explicit cancellation propagation for cancellable I/O and long-running work;
- async APIs that do not block or hide background work;
- immutable or deliberately mutable public contracts with compatibility tests;
- central package/version management and locked/repeatable restore as appropriate;
- deterministic builds, Source Link, analyzers, formatting, dependency audit, SBOM, and provenance for distributed artifacts;
- unit, integration, architecture, contract, and acceptance tests selected by risk;
- ArchUnitNET or an equivalent deterministic check when project or assembly dependency rules need executable enforcement;
- Reqnroll when business-critical multistep behavior benefits from executable examples.

Explicit intake selections and the versioned Program Kit .NET defaults are adopted through the
bootstrap assessment gate. Choices outside that reviewed baseline remain Proposed until accepted by
ADR. ORM, serializer, and test-framework details use the baseline defaults when available rather
than becoming mandatory human questions.

The exact SDK in the selected Program Kit profile's managed `global.json` is authoritative even
when `dotnet --version` reports an older or different local SDK. Treat that mismatch as an actionable
install/upgrade requirement and urge exact, side-by-side remediation. Keep the local SDK as project
truth only after the user explicitly approves the `managed-toolchain-version` override recorded by
the bootstrap decision contract; current-version research alone is not an override.

## Modular DDD topology

Apply `modularity-and-contracts.md` and `vertical-slicing.md`. A default solution graph is:

```text
external ProgramKit.Host
  -> packaged activatable implementations selected by shells.json

Application.Context.Core
  -> .NET, lightweight framework abstractions, and explicitly accepted Core dependencies only

Application.Context
Application.Context.Api
Application.Context.PostgreSql
Application.Context.Import.Excel
  -> Application.Context.Core
  -> capability-specific helper packages when needed

Application.Consumer.Provider
  -> Application.Consumer.Core
  -> Application.Provider.Core

Application.Persistence.PostgreSql
  -> selected per-context PostgreSQL providers as an optional composition preset
```

The external host is the composition root and loads the selected feature package closure; the
consumer repository does not create a host project unless an explicit accepted opt-out selects a
custom runtime. A runtime feature is an activation type and stable identity, not a project-name
layer. Project, package, and namespace names MUST NOT contain a generic `.Feature` segment. Use
domain language and name an implementation by the behavior, protocol, provider, consumer/provider
bridge, helper, or composition preset it contributes. A class such as `CatalogFeature` remains
appropriate inside `PriceCalculator.Catalog`.

`Application.Context.Core` defines the context's deliberately stable semantic surface: aggregates,
entities, value objects, domain commands and queries, business result models, invariants, policies,
evaluators, lifecycle states and transitions, domain events, contributor contracts, registry
descriptors, and semantic capability interfaces. It excludes CShells activation, DI registration,
ASP.NET wire types, middleware, EF/provider types, persistence records, migrations, serializers,
vendor SDKs, and private implementation interfaces. Core must not become a catalogue of every type
that could possibly be shared.

Do not create `Domain`, `Contracts`, `Application`, or `Infrastructure` projects as generic
horizontal layers. Create a `.Core` only for an identified context or cohesive subdomain. Put the
default activatable implementation in the domain-named project, HTTP adaptation in `.Api`, and
technology/provider behavior in packages such as `.PostgreSql`, `.Import.Excel`, or `.Import.Json`.
Use `Application.Consumer.Provider` for a consumer-owned cross-context bridge, such as
`PriceCalculator.Forms.Catalog`, which implements a Forms capability using a Catalog-published
capability while translating between their semantic models.

Do not create a solution-wide `Core`, `Common`, or `Shared` project as a default dependency sink.
Keep a genuinely shared semantic kernel small, jointly owned, versioned, and backed by an Accepted
ADR. Name it for the business language it owns rather than `Shared`.

## Feature references and inheritance

- Implementations of a semantic capability depend on its owning `.Core`; they do not depend on each
  other.
- A concrete feature-to-feature `ProjectReference` is forbidden by default.
- Concrete inheritance does not create an exception merely for code reuse.
- A feature-family extension may reference an explicitly designed abstraction or abstract base only
  under the ownership, substitutability, ADR, and allowlist rules in `modularity-and-contracts.md`.
- `InternalsVisibleTo` is forbidden. Tests and probes exercise the same public contracts and
  composition seams available to consumers; they do not receive privileged access to implementation
  details. When a behavior cannot be verified that way, introduce a deliberately owned public
  abstraction or test it through the package's externally observable runtime behavior.
- CI validates both the declared MSBuild `ProjectReference`/`PackageReference` graph and compiled
  assembly dependencies. The declared graph is authoritative even when a reference has not yet
  produced a CLR type dependency. Exact Accepted exceptions are allowlisted; naming conventions
  alone are insufficient enforcement.

## Program Kit host and CShells profile mapping

When .NET is selected, adopt the application-neutral `ProgramKit.Host` and its CShells/Nuplane composition model as the
automatic Program Kit default unless intake explicitly opts out. This default uses CShells as the
runtime composition mechanism; it does not imply that shells are tenants or bounded contexts.
Record the preview packages and package sources as a material acknowledgement in the assessment
review packet. Do not download or restore them merely by approving architecture.

Treat Package Source Mapping as source routing, not as a Program Kit dependency allowlist. The
scaffolded configuration maps the protected `CShells` and `Nuplane` namespaces to their approved
preview feeds; a generic nuget.org mapping accepts other public packages and their transitive
closures. Consumers own dependency selection and may add private sources with specific namespace
mappings. Keep dependency approval in the consumer's version pins, lock files, architecture rules,
security checks, and accepted decisions rather than requiring Program Kit to enumerate package IDs.

An explicit opt-out may select a conventional ASP.NET Core host. Record why the Program Kit host is
not suitable and which composition, packaging, task, and deployment responsibilities the project
then owns.

When accepted:

- feature projects reference `CShells.Abstractions` or, for web composition,
  `CShells.AspNetCore.Abstractions`;
- only the host/composition project references the full `CShells` and `CShells.AspNetCore` runtimes;
- the host bridges Nuplane-loaded feature assemblies into CShells and owns only its runtime configuration;
- an `IShellFeature` or `IWebShellFeature` is a composition adapter, not the domain model;
- every packaged feature declares `[ShellFeature("<exact ProgramKitFeatureIdentity>")]`; CLR,
  package, runtime-catalog, and `shells.json` identities are one case-sensitive contract;
- `ConfigureServices` registers implementations of owned domain or contract interfaces and contains
  no business policy;
- feature configuration is bound to feature-owned typed options using the accepted .NET options
  mechanism, with startup validation, safe defaults, and secret-free checked-in values;
- feature constructors use only permitted root services and shell construction context; behavior
  resolves composed services only after the shell provider exists;
- CShells `DependsOn` feature metadata expresses activation ordering and availability coupling, not
  permission to reference another feature's implementation or store;
- business features normally collaborate through contracts rather than feature dependencies;
- named platform-feature dependencies are documented with optionality, ordering, failure behavior,
  and compatibility treatment;
- all CShells packages are pinned to the same researched version and exercised through composition,
  isolation, routing, reload, drain, and upgrade tests appropriate to the accepted capabilities.

Shells are runtime isolation contexts; they are not bounded contexts. Verify tenant identity,
authorization, service lifetimes, root-service copying/exclusion, configuration isolation, route
ownership, background scopes, drain semantics, and recovery before treating a shell as a security or
tenancy boundary.

## ASP.NET Core Minimal API slices

Use built-in ASP.NET Core Minimal APIs as the default HTTP candidate when a vertical slice exposes an
HTTP boundary. A web feature maps a feature-owned `RouteGroupBuilder` from
`IWebShellFeature.MapEndpoints`; each slice contributes a small mapping method and co-located wire
contracts, policies, handler/orchestration, and tests.

Require every public operation to define:

- a stable route, HTTP method, endpoint name or operation identity, and owning feature;
- explicit authorization or a deliberate anonymous decision;
- request and response wire contracts distinct from domain entities and persistence models;
- validation and trust-boundary conversion;
- success and material failure statuses with a stable error schema;
- cancellation propagation and explicit timeout, retry, idempotency, and concurrency behavior where relevant;
- OpenAPI metadata and compatibility evidence when externally consumed;
- traceability to the owning vertical slice and verification of the observable outcome.

Endpoints remain thin transport adapters. They may coordinate a simple transaction script or invoke
application/domain behavior, but they do not own business invariants. Endpoint filters handle
transport-cross-cutting concerns only and must not become a hidden domain pipeline.

The selected Program Kit web runtime configures authentication schemes, middleware ordering, common
Problem Details, correlation, standard security headers, CORS, and OpenAPI infrastructure from
host/deployment configuration. Consumer `.Api` packages
own route groups, wire contracts, mapping, endpoint-specific bounds, OpenAPI metadata, stable
application permission identities, and authorization/rate-policy requirements. They do not create a
root `Administration.Api` or `Platform.WebBoundary` package merely to repeat host plumbing.

Register each semantic capability implementation in the activatable package that implements it.
Before implementation, record the capability, its owning Core project, concrete implementation,
implementing project, registration entry point, and the implementation project's activated feature
identity in `artifact-ownership.json.runtimeComposition`. Endpoint implementations never reference
persistence providers merely to make the external host aware of both packages.
Test route collisions, shell prefixes, authorization metadata, schema generation, problem responses,
and dynamic endpoint refresh when those CShells capabilities are used.

For an externally consumed OpenAPI surface, register a consumer-owned contract in
`.program-kit/openapi-contracts.json` before implementation readiness. The contract names the shell and
every route-contributing feature, uses `artifacts/runnable-host/packages` as its package closure, and pins
the managed `ProgramKit.OpenApi.Exporter` and oasdiff versions. Start an empty registry with
`eng/program-kit/openapi_init.py`; these managed tools are adopted baseline choices, not a new consumer
ADR. `eng/program-kit/Build.ps1` then composes those feature packages
without opening a listener or running shell initializers, normalizes and compatibility-checks the result,
runs the separately locked client generator, and finally compiles the application's own TypeScript graph.
The exporter tool is restored only when the registry is non-empty; its dependencies are not added to feature
projects or the application. Generator dependencies remain consumer-selected inside the isolated generator
package, subject to strict peer/engine resolution evidence.

When the application has an authenticated browser boundary, the selected Program Kit host web
profile owns the versioned runtime contract in `../secure-web-profiles.md`. Feature endpoints declare
a stable application permission/policy or explicit anonymous access; they do not select schemes,
parse provider token shapes, implement login/logout, or return tokens. Deployment configuration maps
provider roles, scopes, or claims to canonical application permissions. Resource-specific
authorization handlers stay with the owning `.Api` implementation when generic permission metadata
cannot express the rule.
Do not add a feature-side provider-role parser, canonical `permissions` claim parser, or wrapper
`*PermissionPolicy` around the managed dynamic policy provider. A bodyless/no-effect permission probe
uses only `.RequireAuthorization("permission:<identity>")`. A command or query that changes, reveals,
or admits protected business state additionally invokes the owning resource/state/effect rule.

## Domain and persistence rules

- Model aggregates and rich domain behavior only where business complexity warrants them; simple
  slices may use transaction scripts without bypassing ownership and contract rules.
- Core domain types are POCOs and do not depend on ASP.NET Core, CShells, EF Core, serializers, or DI.
- Core declares the smallest cohesive semantic capabilities its consumers need. One interface may
  contain multiple naturally related methods when they share purpose, consumers, consistency,
  security, availability, ownership, lifecycle, and replacement. Do not create one interface per
  method, table, or aggregate.
- Split a capability when consumers, optionality, security, consistency, performance, evolution, or
  credible provider support differs. A single provider class may implement multiple capability
  interfaces.
- Name capabilities for business intent, such as `IActiveCatalogItemLookup`,
  `ICatalogRevisionLifecycle`, or `IPriceDashboardQueries`; do not prescribe repositories, stores,
  units of work, generic CRUD, `DbSet`, or `IQueryable` boundaries.
- Provider-specific persistence records, mappings, migrations, `DbContext`, SQL/query expressions,
  cursors, and schema details remain private to the provider package. A provider may instead map a
  persistence-ignorant Core POCO directly when no storage concern shapes or escapes through it.
- Cross-context reads use a consumer-owned capability/bridge, an intentionally published Core
  language, a read projection, or an API. Domains exchange business-semantic boundary models, never
  persistence records or another context's internal aggregates.
- Cross-module writes and shared transactions require an Accepted ADR.

## Domain and integration events

Domain-owned Core projects may reference `ProgramKit.DomainEvents.Abstractions` and declare immutable
past-tense events. Activatable implementations register typed handlers; the selected
`ProgramKit.DomainEvents` feature supplies awaited, scoped, sequential in-process dispatch. Handler
order is not a workflow contract. Use an explicit orchestrator when reactions require ordering,
results, retries, compensation, or lifecycle state.

Use a synchronous capability when the caller needs an answer or must observe failure. Use a domain
event for a fact with zero or more independent observers. Plain domain-event publication is not
durable and MUST NOT be described as reliable post-commit, background, broker, or cross-process
delivery. Those requirements trigger the separately tracked Integration Events design and its
transactional outbox, at-least-once, idempotency, retry/dead-letter, ordering, versioning, replay,
retention, security, and observability obligations.

## Profile evidence

Re-verify package APIs and supported framework versions during project research; do not treat this
profile as a package-version pin. Primary sources accessed 2026-08-25:

- [CShells](https://www.nuget.org/packages/CShells) and
  [CShells.AspNetCore](https://www.nuget.org/packages/CShells.AspNetCore) runtime capabilities;
- [CShells.AspNetCore.Abstractions](https://www.nuget.org/packages/CShells.AspNetCore.Abstractions)
  for lightweight `IWebShellFeature` feature projects;
- [ASP.NET Core Minimal API route handlers and route groups](https://learn.microsoft.com/aspnet/core/fundamentals/minimal-apis/route-handlers);
- [.NET DDD domain-model guidance](https://learn.microsoft.com/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/net-core-microservice-domain-model)
  and [infrastructure dependency guidance](https://learn.microsoft.com/dotnet/architecture/microservices/microservice-ddd-cqrs-patterns/infrastructure-persistence-layer-design).

## Program Kit runtime and engineering companions

When .NET is selected, `../dotnet-engineering.md` is the mandatory language/runtime profile and
`../dotnet-runtime-and-application-bundles.md` is the mandatory CShells hosting and deployment profile.
Installing Program Kit does not select .NET and does not scaffold these files. The optional sync is not a
prerequisite for technology-neutral governance or proposed quality gates. Run
`speckit.program-kit-dotnet.sync` in write mode only after an Accepted .NET technology decision, an Accepted
ADR selecting the Program Kit host/runtime, and explicit human approval for the pinned preview packages and
preview NuGet sources. The command installs or updates the hash-tracked repository baseline. The standard
runtime is `ProgramKit.Host`; consuming repositories generate
feature packages and a digest-identified runnable application image, not a custom host project.
