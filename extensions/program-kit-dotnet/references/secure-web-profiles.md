# Secure web boundary profiles

## Purpose

This is an implementation contract, not a menu of unanswered questions. Once a profile is selected,
the Program Kit host web runtime supplies its authentication, common authorization, HTTP,
configuration, operational, and test behavior. An application `.Api` implementation supplies route
ownership, wire contracts, stable permission/policy metadata or an explicit anonymous declaration,
and its business outcomes; it does not create an application-root web-boundary feature.

The profile contract version is recorded in `docs/architecture/bootstrap-decisions.json` and
`.program-kit/web-profile.json`. Program Kit upgrades may add capabilities compatibly; a breaking
behavior change requires a new profile version.

## Security assurance contract

Both authenticated profiles inherit:

- threat model `program-kit-web-threat-model-v1` from `web-security-threat-model.md`; and
- evidence profile `program-kit-web-security-evidence-v1` from
  `web-security-evidence.json`.

The evidence register is authoritative for source status, threat-to-control traceability,
configurable-default rationale, residual risks, verification levels, and mandatory review triggers.
It distinguishes final standards and specifications, government guidance, an active IETF draft,
peer-reviewed formal analyses, platform guidance, industry frameworks, and Program Kit policy. A
local policy or operational default is never presented as a normative standard or scientific
result.

A consuming project inherits this assurance baseline by exact ID. Its architecture records only
additional assets, threats or assumptions; configured-value overrides; accepted residual risks; and
stronger controls. Any security-sensitive override requires an Accepted ADR naming the owner,
evidence, review condition, and regression test. Feature specifications consume the resulting
boundary and do not reopen inherited protocol decisions.

## Selection

| Application shape | Selected profile | Rule |
| --- | --- | --- |
| Browser UI, no explicit override | `bff-cookie-v1` | Secure default |
| Same-origin or proxyable browser UI | `bff-cookie-v1` | Preferred |
| Independently hosted static SPA that must call APIs directly | `spa-pkce-v1` | Explicit choice and acknowledgement |
| No browser authentication boundary | `none-v1` | Explicit or derived non-web choice |

An unqualified request for “SPA authentication” does not select browser-held tokens. A SPA is a UI
architecture; it can and normally should use the BFF profile.

## Common contract

### Runtime configuration

Configuration binds to the selected shell's `ProgramKit:Web` section and is validated when that
shell activates. Secret values come from the environment or a secret provider and never from
committed settings. For the scaffolded `default` shell, the BFF client-secret environment key is
`CShells__Shells__default__Configuration__ProgramKit__Web__ClientSecret`. For `spa-pkce-v1`, the
scaffold-owned `.program-kit/spa-pkce.json` is the typed security input; synchronization validates it
and derives the managed shell overlay, Keycloak registration, and browser contract. Consumers
change that input and resynchronize rather than editing a derived managed file.

- The active `ProgramKit.Authentication.BffCookie` or `ProgramKit.Authentication.SpaPkce` feature is
  the profile discriminator; runtime code does not branch on a profile enum.
- `Authority`: HTTPS issuer URL; HTTP is permitted only by an explicit local-development setting.
- `BackchannelAuthority`: optional server-reachable discovery authority. It changes only metadata
  retrieval; `Authority` remains the validated issuer and browser-facing URL. The managed local
  Compose topology uses Keycloak's dynamic backchannel support and a private shared network, never
  a container override for `localhost`.
- `ClientId`; `ClientSecret` is required only for BFF.
- `Audience`, `Scopes`, provider `RoleClaim` (default `roles`), and canonical `PermissionClaim`
  (default `permissions`).
- `RolePermissions` and `ScopePermissions`: deployment-owned exact mappings from provider values to
  application permissions. Empty mappings grant nothing and are the scaffold default because Program
  Kit cannot invent an application's permission vocabulary.
- exact `AllowedOrigins`; wildcards and origin reflection are rejected.
- callback, signed-out callback, remote-signout, and access-denied paths.
- discovery/JWKS, remote-authentication, and back-channel time budgets.
- session idle and absolute lifetimes; the absolute lifetime bounds refresh-token use. For SPA-PKCE,
  these are enforced jointly by the provider SSO session, the browser session adapter, and API token
  lifetime validation; the API host settings alone do not create a browser session.
- cookie name, `Secure`, `HttpOnly`, and `SameSite` policy.

Invalid or incomplete selected-profile configuration prevents startup with a path-specific error.
Checked-in local settings contain identifiers and loopback URLs only; production secrets and origins
must be supplied by deployment.

### Provider-neutral capability boundary

Program Kit runtime features model standards-based authentication capabilities, never the currently
bundled identity-provider product. Interactive OIDC/OAuth, client credentials, downstream API token
attachment, RFC 8693 token exchange, DPoP sender constraint, assurance/step-up (`acr`/`amr`), and
discovery/JWKS key rollover use provider-neutral options and contracts. Their package names, public
types, configuration paths, handlers, and errors must not contain Keycloak concepts. Provider HTTP
endpoints are discovered or explicitly configured; runtime code never assumes a realm path, admin
API, container hostname, or provider-specific claim shape.

Keycloak is the built-in local identity adapter and conformance fixture. Its realm renderer maps the
neutral capability contract to Keycloak clients, scopes, protocol mappers, roles, authentication
flows, keys, and themes. A future provider adapter must be able to render the same functional
contract without changing application features or canonical permissions. A capability is not
considered supported merely because the Keycloak fixture can perform it: it needs a provider-neutral
runtime contract when applications participate in the protocol, deterministic wire-level tests, and
at least one real-provider acceptance path. A genuinely provider-exclusive facility may use a
provider-named adapter or package, but that exception must be explicit and cannot leak into the
common authentication packages.

The local-development HTTP exception follows this boundary too. Public authorities may use HTTP
only on a loopback origin under the explicit development override. A container/provider hostname is
not special-cased; server-only routing belongs in `BackchannelAuthority`.

The local Keycloak fixture advertises `http://localhost:8080` to browsers while the application
container retrieves discovery through `http://program-kit-identity:8080`. Keycloak derives its
backchannel endpoints from that private request and retains the public issuer/frontchannel URLs.
The application and identity Compose projects join the named `program-kit-local` network; replacing
container `localhost` is forbidden because it changes loopback semantics for every process.

### Authentication verification tiers

Core CI continuously proves the portable contract: configuration validation, issuer/audience/key/lifetime
validation, claims and permission normalization, BFF and SPA-PKCE journeys, machine identity, token
exchange, downstream routing, refresh-token replay rejection, DPoP request binding, and deterministic
discovery/JWKS rollover. These checks must remain unattended, deterministic, and provider-neutral except
for the pinned local provider used as a baseline conformance fixture.

Specialized authenticator and provider-administration lifecycles run through
`scripts/Test-AdvancedAuthentication.ps1`. This explicit local suite proves real TOTP enrollment and
challenge, passkey enrollment and passwordless sign-in, one-time recovery-code use and replay rejection,
branded multipart SMTP-delivered password reset, email verification and required-action messages,
low-to-high ACR step-up, provider signing-key promotion/overlap/retirement, and provider administration
through a least-purpose disposable service account. DPoP issuance, token exchange, key binding,
wrong-key rejection, and authorization-server
proof replay are exercised by the pinned provider fixture; portable client/resource-server tests cover
proof generation, persisted key identity, nonce challenge/consumption, request binding, and replaceable
distributed replay/nonce seams. Moving these journeys out of per-change CI does not weaken their
acceptance contract: an advertised capability still requires a green portable contract and a green
real-provider path before publication. Run the advanced suite whenever authentication runtime, the
identity adapter/theme, or the pinned provider version changes.

### Identity administration boundary

`ProgramKit.Identity.Admin.Abstractions` owns the provider-neutral business-orchestration contracts.
Consumers can create and maintain users and applications, manage reusable scopes and user-attribute
claim mappings, assign realm roles and groups, initiate credential/enrollment actions, and observe or
revoke sessions without referencing a provider product. `ProgramKit.Identity.Keycloak.Admin` implements
those contracts and contributes separate CShell features for Users, Applications, Scopes, Access,
Enrollment, and Sessions. Selecting one subdomain does not register another.

Keycloak-specific facilities remain behind separately selected AuthenticationFlows, IdentityProviders,
Organizations, and RealmOperations features. RealmOperations contains key metadata, audit-event
configuration/queries, and brute-force lockout maintenance because those structures and permission
models are provider-specific and high privilege. Realm deletion/import, user impersonation, private-key
export, arbitrary Admin REST transport, and persisted admin username/password login are deliberately not
exposed. Those operations have destructive or privilege-escalating semantics that should not become an
accidental application dependency. Each enabled feature should receive a distinct confidential service
account with only its required fine-grained administration permissions; pipeline application/scope
provisioning should not share credentials with subscription-driven user enrollment.

The deterministic consumer probe verifies feature isolation, safe service-account token caching, path
encoding, portable projections, enrollment-action mapping, and every supported endpoint family. The
advanced real-provider probe performs create/use/delete lifecycles for users, roles, groups, applications,
scopes, claim mappers, credentials, sessions, and key metadata. Provider-specific JSON is confined to the
explicit provider interfaces so a future adapter can implement the common orchestration contracts without
consumer changes.

The complete endpoint selection, exclusions, and service-account permission model are documented in
`references/keycloak-admin-api.md`.

The presence of a configurable value does not mean its default is universal. The evidence register
classifies every material default and states when it must be reviewed. In particular, identity time
budgets are service-objective choices, session durations depend on assurance level and product risk,
local identities and ports are development fixtures, locale selection is a product default, and CSP
must be tightened or minimally adapted to the actual frontend resource model.

### Authentication and claims

- Issuer, audience, signature, and token lifetime are validated.
- The stable application subject is the issuer plus `sub`; email and display name are not keys.
- provider roles/scopes/claims are normalized into canonical application permissions using
  deployment-owned mappings; unknown inputs grant nothing. An identity provider may alternatively
  issue the configured canonical permission claim directly.
- policies use stable application requirements such as `permission:catalog.administer`; endpoint
  implementations do not parse provider token shapes or hard-code provider role names.
- consumer features also do not reparse the normalized canonical permission claim. The managed
  dynamic `permission:<identity>` policy is the endpoint authority. A no-effect access probe stops
  there; only a real resource/state/effect decision adds an owning `.Api` authorization handler.
- endpoints require authenticated users by fallback policy unless they explicitly opt into anonymous
  access. Login initiation and protocol callback endpoints are the standard anonymous set; any health
  endpoint needs a separately owned contract.
- authentication failures use `401`; authenticated policy failures use `403`. API failures are
  `application/problem+json` with stable `code`, `traceId`, and no provider internals.

### HTTP and telemetry

- Every request has a validated or generated correlation ID, returned as `X-Correlation-ID` and
  included in problem responses and logging scopes.
- Security headers include no-sniff, frame denial, a restrictive referrer policy, permissions policy,
  and a profile-appropriate CSP. HSTS is enabled outside local development.
- CORS is disabled for the same-origin BFF. SPA PKCE permits only configured exact origins, headers,
  and methods; credentials are not combined with wildcard origins.
- `ProgramKit.Host` does not expose or aggregate application health. Until CShells defines a feature-health
  contribution interface, selected features own any liveness/readiness surface and its redaction contract.
- identity-provider navigation is outside app-controlled response budgets. Product SLOs for
  discovery, JWKS, callback, API, and session operations are feature/deployment decisions and are
  not inferred from Program Kit's separate five-second local preflight default.

### Identity provider fixture

The selected local profile supplies a pinned Keycloak container, imported realm, bearer-only API
audience/scope, exactly one interactive client, and three non-production personas: authorized user,
administrator, and authenticated user without the provider role that maps to the requested
application permission. The unselected interactive client is absent from the desired state, not
disabled or retained for convenience.

| Selected profile | Interactive client present | Interactive client absent |
| --- | --- | --- |
| `bff-cookie-v1` | Confidential BFF client with its exact redirect and post-logout URIs | Public SPA-PKCE client |
| `spa-pkce-v1` | Public SPA-PKCE client with its exact origins, redirects, and post-logout URIs | Confidential BFF client |
| `none-v1` | None; the identity fixture is not installed | Both authenticated-profile clients |

The profile-neutral realm source contains only shared provider state and the bearer-only API client.
Synchronization composes it with the one client contribution owned by the selected profile, then
validates the exact client set before and after the transaction. Profile-neutral documentation and
validation describe BFF and SPA-PKCE as alternatives; they never prescribe their union. Fixture
credentials are local-test data and are never reused in deployed environments. SPA redirect and
post-logout registrations are exact routes derived from `.program-kit/spa-pkce.json`; wildcard
registrations are rejected before Compose starts.

## `bff-cookie-v1`

- The profile activates `ProgramKit.Authentication.BffCookie`, an `IWebShellFeature` plus ordered
  `IMiddlewareShellFeature`; the generic host contains no BFF endpoints, authentication handlers,
  antiforgery middleware, or response-format policy.
- The selected Program Kit host web runtime is a confidential OIDC client using authorization code
  flow and PKCE.
- Access and refresh tokens remain in a server-side `ITicketStore`; the browser cookie contains only
  an opaque protected session key.
- Cookie defaults are `HttpOnly=true`, `Secure=Always`, `SameSite=Lax`, a `__Host-` name, no domain,
  and path `/`. Local HTTP is supported only by an explicit development override and uses visibly
  development-only cookie names because browsers reject `__Host-` cookies without `Secure`.
- `GET /bff/login?returnUrl=/safe/path` starts login. Return URLs must be local and relative.
- `GET /bff/user` returns a minimal session projection (authentication state, validated issuer,
  non-empty subject, display name, and canonical permissions) and never returns tokens, provider
  roles, or the raw claims principal. An OIDC response without both `iss` and `sub` cannot establish
  a session; an anomalous existing ticket missing either claim is cleared and returns `401`
  `authentication_identity_invalid`.
- `GET /bff/antiforgery` issues an antiforgery request token for in-memory use by the UI.
- unsafe same-origin `/api` requests require the token in `X-CSRF-TOKEN`. Browser logout uses the
  managed `bff-session.ts` adapter: it opens a same-origin auxiliary browsing context during the
  user gesture, obtains `/bff/antiforgery`, and submits a top-level `POST /bff/logout` form using
  `__RequestVerificationToken`. A missing, invalid, or cross-site token fails before local session
  mutation. Scripted cross-origin `fetch` is not a logout-navigation mechanism.
- session renewal is server controlled and cannot extend beyond the configured absolute lifetime.
  Expired or unrecoverable sessions terminate locally and return `401` to API requests.
- logout deletes the local server ticket and cookie first, then attempts RP-initiated provider
  logout. A failed or unavailable provider logout cannot restore the local session. The v1 profile
  does not claim back-channel logout; that requires verified logout-token validation in a later
  compatible profile.
- cookie redirects are converted to `401`/`403` problem responses for `/api`; interactive BFF
  endpoints retain protocol redirects.

## `spa-pkce-v1`

- The profile activates `ProgramKit.Authentication.SpaPkce`, an ordered `IMiddlewareShellFeature`
  (and endpoint-capable `IWebShellFeature`); the generic host contains no bearer handler, CORS
  policy, or authentication response formatting.
- The browser is a public authorization-code client with PKCE S256 and no client secret.
- The API accepts bearer tokens only and validates issuer, audience, signature, and lifetime.
- access and refresh tokens are memory-only by default. Browser refresh terminates the local session
  unless the explicitly selected client library can re-establish it using provider state without
  durable token storage.
- silent renewal, if enabled, is bounded and failure transitions to a locally signed-out state.
- logout clears all local authentication state before RP-initiated provider logout.
- exact API origin, allowed browser origins, redirect URIs, logout URIs, scopes, and renewal timeouts
  are part of the selected profile configuration.
- Keycloak authoritatively enforces the configured idle and maximum SSO/client-session lifetimes;
  the API authoritatively enforces token `exp`; and the consumer SPA imports the managed
  `.program-kit/eng/web/spa-session.ts` adapter to enforce local idle expiry and the non-extendable
  `auth_time + absoluteMinutes` deadline. A missing trusted `auth_time` is an authentication failure,
  not a reason to start a new absolute window. Silent renewal retains the original `auth_time` and
  cannot move that deadline.
- The browser announces only a `signed-out` event over `BroadcastChannel`; it never sends a token or
  session identifier between tabs. Receipt clears local authentication in the other tab. Logout
  clears local state and broadcasts first, then attempts provider logout; provider failure leaves
  every local tab signed out and produces the documented unavailable outcome.
- `.program-kit/eng/web/vite.security.mjs` owns browser-response headers for local Vite development
  and preview. Consumer-owned `vite.config` imports `programKitSpaSecurity` with exact API and
  identity origins. A production static server or edge must translate the checked
  `spa-security.json` contract; the production TLS terminator separately owns HTTPS and HSTS, so
  local HTTP never claims them.
- `bff-cookie-v1` serves the browser and API through the Program Kit host's same-origin security-
  header middleware. Its WEB-V3 suite asserts those headers on a BFF response. `Test-Web.ps1`
  rejects `-ViteConfig` for BFF consumers because that adapter is exclusive to an independently
  hosted `spa-pkce-v1` client.
- The production CSP permits self-hosted scripts/styles by default. Add an exact source, nonce, or
  hash only after resource review; do not add `unsafe-inline` or wildcard sources. Keycloak
  top-level navigation needs no CSP source, while browser discovery/token calls need its exact
  origin in `connect-src`. Another approved SPA server must implement the same header contract and
  pass WEB-V1 configuration and WEB-V3 browser assertions.

## Local preflight ownership

`.program-kit/eng/preflight.py` runs before any host or Compose command. It checks the Docker CLI,
then calls the daemon directly with a bounded five-second Program Kit development default. The
timeout is configurable through `PROGRAMKIT_PREFLIGHT_TIMEOUT_SECONDS`; it is a tooling hang budget,
not a product SLO. `PKP001` through `PKP004` stop on the first invalid setting, missing CLI, timeout,
or stopped daemon without cascading commands or echoing daemon error details.

## Mandatory verification

Every selected web profile implements assurance levels `WEB-V1` through `WEB-V3` from the evidence
register. A production deployment additionally owns `WEB-V4`. Every control must retain at least one
prevention or detection mechanism and its mapped negative evidence; a passing happy-path login is
not security evidence by itself.

The shared contract suite plus profile-specific browser suite verifies:

1. Anonymous API call is `401`; a principal without the requested application permission receives
   exactly `403`; a principal with it succeeds with any `2xx` response, including `200` and `204`.
   Redirects and every other non-`2xx` response fail the authorized permission probe.
2. Permissions are derived from the configured canonical claim or exact provider-role/scope mappings;
   unknown or missing values grant nothing.
3. Login returns only to a validated local path.
4. Browser refresh follows the selected session contract without leaking tokens to persistent
   storage, URLs, logs, or rendered output.
5. Session expiry and failed renewal produce a deterministic locally signed-out UI.
6. Local logout remains complete when the provider is unavailable; remote logout success is tested
   separately from that provider-controlled failure.
7. BFF unsafe requests without or with an invalid antiforgery token fail; valid same-origin requests
   succeed. SPA preflight and disallowed-origin cases are tested instead.
8. Security headers, correlation IDs, and Problem Details are asserted. Feature-owned operational probes
   require their own degradation/recovery contract and tests when selected.
9. Playwright runs the real local Keycloak login for the authorized, administrator, and wrong-role
   personas. Authentication state files are generated under test artifacts, treated as secrets, and
   never committed.
10. Authentication suites disable traces, screenshots, and video by default. A project may retain a
    separately reviewed, demonstrably redacted non-authentication artifact, but it must not enable
    capture for login, callback, renewal, logout, or authenticated storage/network activity.

Unit mocks may test feature policy logic, but they do not replace this browser/provider contract.

## Managed ownership and extension points

| Artifact | Ownership and supported change path |
| --- | --- |
| `.program-kit/spa-pkce.json` | Scaffold-owned typed SPA security input. Edit it, then rerun sync. |
| `hostsettings.json` | Scaffold-owned host infrastructure only: eager activation and Nuplane package loading. It contains no auth profile configuration. |
| `deploy/keycloak/program-kit-realm.json` | Managed derived local fixture composed from shared provider state and exactly one selected-profile client. Never edit it; change the selected profile (or SPA input) and sync. |
| `deploy/compose.application.yml` | Managed API-host composition. SPA-PKCE never receives a client secret. |
| SPA process composition | Consumer-owned Compose overlay passed to `Dev.ps1 -ComposeOverlay <path>` or an independently managed static-server process. |
| `.program-kit/eng/Dev.ps1` and `Test-Web.ps1` | Managed launch/test entry points. Use their parameters; do not fork them. |
| `.program-kit/eng/web/playwright.config.ts` | Managed secret-safe authentication-test configuration. Authentication capture remains off. |
| Consumer `vite.config` | Consumer-owned adapter point importing `programKitSpaSecurity` and the SPA session adapter. |
| `.program-kit/web-profile.shells.json` | Managed selected-profile contribution: activates exactly one authentication feature and supplies its shell-scoped configuration. |
| `shells.json` | Consumer-owned CShells composition. It is loaded after the managed profile contribution, so a consumer can set `ProgramKit.Web.ProblemDetails` to `false` and activate its own exception feature. |

## CShells feature composition

`ProgramKit.Host` owns only Nuplane/CShells bootstrapping, eager shell activation, `MapShells()`, and
process lifetime. Web behavior is package-owned:

- `ProgramKit.Authentication.BffCookie` owns confidential OIDC/cookie configuration, server-side
  tickets, antiforgery middleware, and `/bff/*` endpoints.
- `ProgramKit.Authentication.SpaPkce` owns JWT bearer validation and exact-origin CORS.
- `ProgramKit.Authentication` is the shared dependency for canonical permission mapping and exposes
  `IAuthenticationErrorWriter`; consumers may replace its default error representation.
- `ProgramKit.WebDefaults` owns the default localization, HSTS, correlation, and security-header
  middleware.
- `ProgramKit.Web.OpenApi` owns the optional shell OpenAPI endpoint.
- `ProgramKit.Web.ProblemDetails` owns the optional default exception/status response format. It is
  deliberately not an authentication-feature dependency, so consumers can deactivate it and bring
  their own global exception-handler feature without forking the host or an auth package.

Per-shell exception middleware covers downstream shell middleware and endpoints. A failure before
CShells resolves and enters a shell remains a host-infrastructure failure and is not reformatted by
an application feature.

## Review and non-claims

The profile must be reviewed when its standards or platform guidance changes, when the browser-app
draft becomes final, when the runtime/provider/library/deployment model changes, after a relevant
incident or advisory, for a security-sensitive override, and at least every twelve months. Review
updates the evidence register's `lastReviewed` value and either preserves the profile contract or
introduces a versioned migration.

Program Kit does not claim that browser tests, security headers, BFF, PKCE, or OIDC alone make an
application secure. It does not cover compromised identity providers or hosts, business-policy
correctness, tenant isolation, abuse controls, privacy classification, production secret/key
management, or risk-specific step-up authentication. Those responsibilities remain visible in the
threat model and the consuming architecture.
