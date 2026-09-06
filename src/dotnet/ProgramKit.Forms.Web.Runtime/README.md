# ProgramKit.Forms.Web.Runtime

An independently selected endpoint-only `CShells.IWebShellFeature` for current and explicitly
identified immutable form releases. Retired releases are not served. Responses carry strong ETags,
bounded cache policy, and `nosniff`; deployments may expose releases publicly or apply a host policy.

The feature installs no authentication, middleware, exception formatting, or Host behavior.
