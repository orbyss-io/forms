# ProgramKit.Identity.Keycloak.Admin

Keycloak Admin REST adapter split into opt-in CShell features. Portable application workflows use
the interfaces from `ProgramKit.Identity.Admin.Abstractions`; Keycloak-only administration stays
behind explicitly named Keycloak interfaces.

Available shell features:

- `ProgramKit.Identity.Keycloak.Admin.Users`
- `ProgramKit.Identity.Keycloak.Admin.Applications`
- `ProgramKit.Identity.Keycloak.Admin.Scopes`
- `ProgramKit.Identity.Keycloak.Admin.Access`
- `ProgramKit.Identity.Keycloak.Admin.Enrollment`
- `ProgramKit.Identity.Keycloak.Admin.Sessions`
- `ProgramKit.Identity.Keycloak.Admin.AuthenticationFlows`
- `ProgramKit.Identity.Keycloak.Admin.IdentityProviders`
- `ProgramKit.Identity.Keycloak.Admin.Organizations`
- `ProgramKit.Identity.Keycloak.Admin.RealmOperations`

Configure `ProgramKit:Identity:Keycloak:Admin`. Use a confidential service-account client with only
the realm-management permissions required by the enabled features. The adapter intentionally does
not support admin username/password authentication.
