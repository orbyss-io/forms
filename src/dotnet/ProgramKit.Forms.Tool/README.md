# ProgramKit.Forms.Tool

Official MCP C# SDK tool definitions over the same `IFormDraftOperations`,
`IFormDraftMigrationOperations`, `IFormSubmissionOperations`, and `IFormAttachmentOperations` used by HTTP and application code.
The package contains no second rules engine.

Tools are owner-scoped, bounded, closed-world, and explicitly annotated. They never accept actor or
administrative flags as arguments. Binary upload/download, scanner control, and administrative
accept/reject are intentionally absent; agents may reference only already-clean attachment IDs.
Draft migration accepts only stable IDs for registered trusted migration handlers, and breaking
release changes cannot silently reinterpret saved data.
HTTP transports use authenticated claims. Stdio hosts must replace `IFormToolActorProvider` with a
trusted local identity provider because no transport principal exists by default.
