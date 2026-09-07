# Orbyss.Forms.Management.Tool

Explicit closed-world MCP tools over the same provider-neutral application services used by the
Forms management API. Tools cover bounded queries, validation, deterministic compilation,
authoring, evidence-bound review, approval, publication, release comparison, and retirement.

Actor identity comes only from the authenticated transport principal. Mutations require stable
idempotency keys, opaque versions, and a repeatable request timestamp. No tool accepts executable
callbacks, provider storage keys, or authorization flags.
