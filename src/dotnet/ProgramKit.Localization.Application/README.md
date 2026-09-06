# ProgramKit.Localization.Application

Provider-neutral implementation of catalog management, bounded search, import preview/application,
review, approval, immutable publication, release lookup, and retirement. It composes the semantic
validator/import coordinator with replaceable catalog, release, and retirement stores.

Every mutation requires an idempotency key. Creates require no version; every other mutation
requires the exact opaque version returned by the preceding command. Catalog storage owns atomic
replay and audit persistence. Publication writes deterministic immutable content before marking the
catalog revision published, so an interrupted command can safely retry. No ASP.NET Core, CShells,
filesystem, database, or identity-provider dependency is introduced.
