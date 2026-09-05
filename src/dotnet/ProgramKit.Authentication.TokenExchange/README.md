# ProgramKit.Authentication.TokenExchange

Provider-neutral OAuth 2.0 Token Exchange (RFC 8693) packaged as a CShells feature. It supports
named token endpoints, resource/audience downscoping, exact scopes, and optional actor tokens. The
service exposes the standard wire contract and keeps provider-specific enablement or policy in the
selected identity adapter.

Application code requests delegation through `ITokenExchangeService`; it never constructs a
provider realm URL or depends on a provider SDK.
