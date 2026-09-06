# ProgramKit.Forms.Abstractions

Provider-neutral contracts for governed form definitions, compilation candidates, immutable
releases, compatibility reports, authoring, lifecycle, and runtime queries. JSON Forms, AJV,
editors, persistence, transports, and CShells activation belong in separate implementation
packages. Forms publish translation requirements in their own language and do not reference a
localization implementation.

Mutation contracts require an idempotency key, expected concurrency token where applicable, and
an audit actor. Implementations must validate identifiers, bounds, lifecycle transitions, schema
content, renderer/action allowlists, and authorization; these transport-friendly records do not
make untrusted input safe by construction.

Optional operational contracts distinguish partial draft validation from authoritative final
submission validation. Drafts and submissions bind to an exact immutable release; access contexts
are server-derived and owner-scoped unless a trusted administrative adapter explicitly broadens
them. Attachment metadata never contains storage paths, and binary content remains unavailable
until declaration, size, signature, and malware-scanner policies approve it.
