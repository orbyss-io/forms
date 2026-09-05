# Program Kit 0.9.9 release evidence

The deterministic suite passed with the exact .NET 10.0.202 SDK, repository analyzers, restricted NuGet
restore, runtime/package coherence, provider-boundary scans, clean scaffold lifecycle, public feature
probes, and solution build at zero warnings and zero errors.

Provider-neutral probes cover client credentials, token exchange, downstream routing, DPoP proof
generation/enforcement/nonce/replay seams, ACR/AMR/authentication-age assurance, and discovery/JWKS
rollover. The Keycloak Admin consumer probe proves independent CShell feature registration, encoded
paths, bounded client-credentials authentication, safe token caching, endpoint shapes, and portable
contract projections.

The explicit advanced suite passed against disposable Keycloak 26.7.3 containers and real Chromium:
TOTP, passkeys, recovery codes and replay rejection; SMTP password recovery; branded multipart reset,
verification and execute-action email; low-to-high ACR step-up; key promotion/overlap/retirement; and a
real create/use/delete Admin REST lifecycle for users, roles, groups, clients, scopes, claim mappers,
credentials, sessions, and key metadata.

Repository-wide scanning found no `InternalsVisibleTo`. The paid live bootstrap acceptance was not
requested and is outside this release evidence.
