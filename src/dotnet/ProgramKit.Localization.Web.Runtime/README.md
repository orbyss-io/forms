# ProgramKit.Localization.Web.Runtime

An independently selected `CShells.IWebShellFeature` for immutable localization resolution and
scope bundles. It does not expose catalogs, imports, exports, lifecycle actions, or persistence.

Runtime reads are public by default for login, marketing, and other pre-authentication pages, but a
consumer can require its default or a named authorization policy. Responses use release-derived
ETags, bounded cache headers, and `nosniff`; the feature does not install authentication middleware
or a global response format.
