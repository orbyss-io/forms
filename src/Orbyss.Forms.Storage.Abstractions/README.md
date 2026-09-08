# Orbyss.Forms.Storage.Abstractions

Replaceable persistence ports for editable form aggregates, immutable published form releases, and
separate retirement state. Implementations must treat a
release identifier as create-only: writing identical content is an idempotent replay, while writing
different content for an existing identifier is a conflict.

The package also defines provider-neutral stores for draft/submission aggregates, attachment
metadata, and quarantined/promoted binary content. Implementations must keep provider keys out of
public contracts, make optimistic commands atomic, persist exact idempotency replays and
server-observed audit evidence, bound enumeration/history/documents, and preserve immutable
submitted payloads.
