# Orbyss.Forms.Management

Provider-neutral orchestration for editable form definitions, deterministic compilation, evidence-
bound review, approval, immutable publication, retirement, and bounded catalog/runtime queries.
Every mutation uses optimistic concurrency, durable idempotency, and attributed audit context.

The management package depends on semantic and storage ports and uses the JSON Forms validator and
compiler implementation. Its `OrbyssFormsManagementFeature` composes the default catalog,
compatibility, authoring, query, and release-lifecycle services. Consumers still select persistence,
HTTP features, and MCP tool contributors independently.
