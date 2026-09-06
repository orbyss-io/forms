# ProgramKit.Forms.Storage.InMemory

Complete bounded in-memory implementations of the Program Kit Forms storage ports for deterministic
tests, UI harnesses, samples, and local development. Definitions, releases, retirement, drafts,
submissions, attachment metadata, quarantine, exact idempotency replay, audit history, and opaque
optimistic versions follow the same public contracts as durable adapters.

State is process-local and intentionally disappears when the process ends. It is not a production
durability default. Consumers retain ownership of production persistence by implementing the narrow
storage abstractions or explicitly selecting a separate adapter such as the filesystem package.
