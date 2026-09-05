# ProgramKit.Authentication.ClientCredentials

Provider-neutral OAuth 2.0 client-credentials acquisition packaged as a CShells feature. Configure
one or more named token-endpoint registrations under
`ProgramKit:Authentication:ClientCredentials:Registrations`. The feature validates every endpoint,
client authentication method, scope, and lifetime setting when its shell activates; caches tokens
per registration; and coalesces concurrent refreshes without logging credentials or token bodies.

Identity-provider adapters generate these portable settings. Application features depend on
`IClientCredentialsTokenProvider` and a registration name, never on an identity-provider SDK,
realm, tenant, or admin API.
