# ProgramKit.Localization.Storage.InMemory

Bounded in-memory implementations of Localization catalog, immutable release, retirement, audit,
optimistic-concurrency, and exact within-process idempotency contracts. This package is intended
for deterministic tests, UI harnesses, samples, and local development.

State is process-local and intentionally disappears when the process ends. Program Kit does not
select a production database or migration model; consumers implement the existing narrow storage
ports or explicitly select another adapter.
