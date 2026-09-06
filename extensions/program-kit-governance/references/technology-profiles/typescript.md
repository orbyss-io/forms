# TypeScript and web profile

Adopt the independent `ui-experience-v1` profile for browser UI: consumer-owned branding and optional
SVG logos, Lucide/custom icons, responsive archetypes, semantic tokens, safe initial-response
metadata, page-level discovery intent, and opt-in analytics. Read `../ui-experience-v1.md` and its
evidence register. Native CSS is the default adapter; accepted frontend/framework decisions remain
authoritative. The isolated UI acceptance graph must not change the application's own npm graph.

When TypeScript or a browser UI is detected, evaluate and normally enforce:

- strict TypeScript mode and no implicit unsafe boundary casts;
- linting and formatting with pinned, non-conflicting tools;
- explicit runtime validation for untrusted API, storage, URL, and message data;
- generated or checked API/schema contracts rather than duplicated handwritten shapes;
- accessible UI semantics and automated checks supplemented by human testing;
- component tests for behavior, integration tests for boundaries, and a small number of high-value end-to-end journeys;
- dependency, lockfile, license, secret, and supply-chain checks;
- bundle-size and performance budgets appropriate to the product;
- safe rendering, CSP, CSRF/session/token treatment, and secret-free client configuration.

For an authenticated browser UI, adopt the versioned secure web profile selected by the bootstrap.
The default is a same-origin BFF even when the UI is a React or other single-page application. The
browser calls `/bff/user`, obtains an in-memory antiforgery token from `/bff/antiforgery`, and sends
same-origin requests; it does not implement OIDC or persist bearer tokens. Direct SPA PKCE/bearer
authentication is an explicit deployment-profile choice, not a frontend-framework default.

Adopt explicit intake choices and applicable versioned Program Kit defaults in the reviewed bootstrap
baseline. Choices not supplied by either source remain Proposed until accepted in the project context;
do not invent a framework merely to make the register look complete.
