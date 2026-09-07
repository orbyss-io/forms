# Orbyss.Forms.Application

Provider-neutral orchestration for editable form definitions, deterministic compilation, evidence-
bound review, approval, immutable publication, retirement, and bounded catalog/runtime queries.
Every mutation uses optimistic concurrency, durable idempotency, and attributed audit context.

The application package depends only on semantic and storage ports. Consumers select the compiler,
validator, persistence provider, HTTP features, and MCP tool contributors independently.
