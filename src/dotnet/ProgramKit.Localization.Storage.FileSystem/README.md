# ProgramKit.Localization.Storage.FileSystem

Atomic, content-verified filesystem storage for editable localization catalogs and immutable
releases. Catalog documents retain durable command replay and append-only audit history, enforce
optimistic versions, and have an explicit size ceiling. Release identifiers are SHA-256-mapped to
filenames, payloads carry their own digest, and immutable content cannot be overwritten.

Writes are serialized within one process. Multi-instance deployments should select a transactional
database adapter rather than share this filesystem adapter across processes. No ASP.NET Core, DI,
or Host dependency is introduced.
