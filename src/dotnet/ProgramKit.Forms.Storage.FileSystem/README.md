# ProgramKit.Forms.Storage.FileSystem

The editable form-definition store uses digest envelopes, bounded enumeration, atomic optimistic
writes, durable exact command replay, and append-only audit history.

The package also provides bounded, digest-verified single-process stores for resumable response
aggregates, attachment metadata, and separately rooted quarantined/available attachment bytes.
Opaque content keys never appear in public attachment contracts. Production multi-instance use
requires transactional metadata and object-storage implementations; filesystem locking is only
process-local.

Atomic, content-verified filesystem storage for immutable form releases. Release identifiers are
SHA-256-mapped to filenames, payloads carry their own digest, and existing identifiers cannot be
overwritten with different content. The adapter has no ASP.NET Core, DI, or Host dependency.
