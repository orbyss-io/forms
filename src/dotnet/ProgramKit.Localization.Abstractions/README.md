# ProgramKit.Localization.Abstractions

Provider-neutral contracts for application-wide translation catalogs, structured scopes, locale
fallbacks, plural/select message arguments, safe import previews, immutable releases, and runtime
bundles. CSV, XLSX, JSON, XLIFF, PO, remote connectors, storage, web endpoints, editors, and CShells
activation belong in separate packages.

Mutation contracts require idempotency, optimistic concurrency, and audit attribution. Import
content remains untrusted: implementations must apply byte, entry, locale, placeholder, message,
scope, and merge-policy limits before returning a preview or changing a catalog. Version-bearing
catalog detail queries supply the opaque token required by the next safe mutation.
