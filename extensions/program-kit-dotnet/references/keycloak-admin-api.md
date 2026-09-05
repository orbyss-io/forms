# Keycloak Admin REST feature boundary

The provider contract follows the official [Keycloak Admin REST API](https://www.keycloak.org/docs-api/latest/rest-api/index.html),
but does not expose a generic `SendAsync` escape hatch. An arbitrary transport would defeat feature
selection, least privilege, migration to another identity provider, and endpoint-level testing.

## Recommended application-facing baseline

| CShell feature | Portable contract | Selected Admin REST resources |
| --- | --- | --- |
| `Users` | `IIdentityUserAdministration` | user search/count/get/create/update/delete |
| `Applications` | `IIdentityApplicationAdministration` | client search/get/create/update/delete and confidential-secret rotation |
| `Scopes` | `IIdentityScopeAdministration` | client scopes, default/optional client assignments, user-attribute OIDC protocol mappers |
| `Access` | `IIdentityAccessAdministration` | realm roles, groups/subgroups, user role mappings, user group membership |
| `Enrollment` | `IIdentityEnrollmentAdministration` | credentials, credential deletion, password reset, execute-actions email for email/password/TOTP/passkey/profile enrollment |
| `Sessions` | `IIdentitySessionAdministration` | user sessions, per-user logout, realm-wide logout |

These are the stable concepts most likely to appear inside provider-independent business workflows:
create an account after payment, provision a machine application and scopes from a pipeline, assign
subscription roles/groups, send enrollment, or revoke access. The abstraction assembly has no CShell,
HTTP, DI, or provider dependency. Another adapter can implement the same interfaces without changing
consumer orchestration code.

## Explicit provider facilities

| CShell feature | Selected Admin REST resources | Reason it remains provider-specific |
| --- | --- | --- |
| `AuthenticationFlows` | flow list/create/copy/delete, execution list/create/update | authenticator aliases, nesting and execution requirements are Keycloak models |
| `IdentityProviders` | provider instances and provider mappers | provider factory/configuration maps are Keycloak SPI-shaped |
| `Organizations` | organization lifecycle and existing-user membership | organization representation and managed-membership semantics are versioned Keycloak facilities |
| `RealmOperations` | key metadata, event configuration/query/delete, per-user/all brute-force failure clearing | realm operational structures and privileges are provider-specific |

Provider-specific representations use `JsonElement` deliberately: those exact structures evolve with
Keycloak and must not be disguised as portable domain models. They are still endpoint-specific methods,
not an unrestricted transport.

## Endpoint families not selected

The following endpoints are useful to administrators but should not be part of the default application
adapter:

- realm create/delete/import and partial import: destructive control-plane operations belong in a
  separately approved infrastructure tool;
- user impersonation: it creates a browser login session with unusually high audit and abuse risk;
- private-key export or arbitrary component mutation: key rotation is an advanced operational workflow,
  while ordinary applications need only public key metadata;
- arbitrary credential material retrieval: authenticators expose metadata and deletion, never secrets;
- client registration access-token generation, initial-access tokens, and installation exports: these
  are bootstrap/control-plane credentials, not business orchestration;
- authorization-services resources, policies, permissions, and decision evaluation: this is a separate
  Keycloak authorization product model and merits its own feature and acceptance suite;
- user-storage/LDAP components and synchronization: these require directory-specific configuration,
  failure recovery, and destructive-sync semantics;
- realm localization, SMTP secrets, themes, and full realm replacement: managed deployment configuration
  owns these; the SMTP email-theme acceptance tests the deployed result;
- attack simulation, session deletion by opaque session identifier, and event deletion are not mixed
  into ordinary user features; the supported maintenance actions remain in `RealmOperations`;
- preview or rapidly evolving workflow endpoints are deferred until their stability and migration
  contract is suitable for a stable Program Kit feature.

Additional provider-specific feature packages should be introduced only with an endpoint inventory,
least-privilege role mapping, typed or deliberately exact provider representation, negative tests, and a
real create/use/cleanup lifecycle. Do not expand `RealmOperations` into a generic Admin REST client.

## Authentication and permissions

The adapter accepts only OAuth client credentials for a confidential service account. It caches tokens
inside their safe lifetime, bounds every request, rejects non-HTTPS servers except an explicit loopback
Development override, encodes realm/resource identifiers, and never logs response bodies or credentials.
Deploy separate clients for user enrollment, CI application provisioning, and realm operations. Grant
only the fine-grained administration permissions needed by each enabled feature; do not grant `realm-admin`
to application workloads.

The core suite uses a recording transport to prove subdomain isolation, request shapes, encoding, token
caching, and public-contract mappings. The advanced suite creates a disposable service account in a
pinned real Keycloak, runs user/access/application/scope/enrollment/session/key-metadata lifecycles through
the public CShell features, and cleans up all resources.
