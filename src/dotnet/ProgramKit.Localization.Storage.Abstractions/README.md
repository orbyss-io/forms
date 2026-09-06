# ProgramKit.Localization.Storage.Abstractions

Replaceable persistence contracts for editable catalogs and immutable published localization
releases. Catalog writes are atomic, optimistic, durably idempotent, and append audit metadata.
Release retirement state is stored separately from immutable message content. Release identifiers
remain create-only: identical content is an idempotent replay and different content is a conflict.
