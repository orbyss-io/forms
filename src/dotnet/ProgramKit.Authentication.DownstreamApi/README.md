# ProgramKit.Authentication.DownstreamApi

Provider-neutral authenticated downstream HTTP calls packaged as a CShells feature. A named API
uses either an application-only client-credentials identity or an RFC 8693 exchanged/downscoped user
identity. The feature does not blindly relay inbound bearer tokens, follow redirects carrying
authorization, accept caller-selected absolute destinations, or expose provider-specific concepts.

Provider adapters generate the relevant token-client and exchange-policy registrations. Application
features call `IDownstreamApiClient` with a configured API name and a relative URI.
