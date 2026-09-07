# Orbyss.Localization.Web.Management

An optional `CShells.IWebShellFeature` that maps localization catalog, validation, import,
export, lifecycle, release lookup, and release-diff endpoints. It does not add authentication,
authorization middleware, persistence, format adapters, or a response-body policy.

Consumers can register `DefaultLocalizationCatalogService` from
`Orbyss.Localization.Application` with their selected catalog/release stores and format
adapters, or provide another implementation of the same public ports, then choose this feature for
shells that own the management plane. All endpoints require authorization;
optional named policies separate read, write, import, and export permissions. Audit actor identity
is derived from configured authenticated claims rather than request content. Import uploads have
both a pre-binding request-body limit and a decoded-byte limit; the configurable decoded maximum is
8 MiB by default and cannot exceed 64 MiB.
