# Orbyss.Forms.Submissions

Optional provider-neutral form data collection for resumable drafts, immutable submissions and
quarantined attachments. Draft data is bound to an exact immutable `FormRelease`; final submission
performs authoritative server validation and snapshots only explicitly selected clean attachments.

Consumers select `IFormSubmissionStore`, `IFormAttachmentStore`, `IFormAttachmentContentStore` and
`IFormAttachmentScanner` implementations. `RejectingFormAttachmentScanner` is deliberately
fail-closed and is not a malware scanner. Production attachment use requires a real scanner.

Select `OrbyssFormsSubmissionsFeature` to register the default draft, migration, submission,
validation, review, and attachment services. Its default attachment policy and scanner both reject
all content; a host must explicitly register an allowlist policy and real scanner before activating
attachments.

The built-in filesystem adapter is appropriate for local/single-process operation. Multi-instance
deployments should use transactional database/object-storage adapters that preserve the same
optimistic concurrency, idempotency, audit, quarantine and immutable-submission contracts.
