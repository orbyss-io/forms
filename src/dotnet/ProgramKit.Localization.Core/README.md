# ProgramKit.Localization.Core

Provider-neutral localization catalog validation and immutable-release runtime resolution.

`LocalizationCatalogValidator` validates locale fallback graphs, structured scopes, message and
argument identity, bounded patterns, and ICU-style plural/select requirements.
`InMemoryLocalizationRuntime` resolves only immutable `LocalizationRelease` entries through the
explicit fallback graph and creates deterministic scope bundles.
`LocalizationImportCoordinator` creates hash-bound previews and applies only an exact validated
proposal with optimistic concurrency and idempotent replay. `DefaultLocalizationReleaseDiffer`
produces deterministic locale-policy and scoped-entry changes for provider-neutral review UIs.
