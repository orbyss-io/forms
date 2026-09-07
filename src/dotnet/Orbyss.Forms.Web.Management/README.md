# Orbyss.Forms.Web.Management

An endpoint-only `CShells.IWebShellFeature` for authenticated form authoring, validation,
compilation, review, approval, publication, retirement, release reads, and compatibility analysis.
It derives audit actors from the validated principal and accepts only command identity, timestamp,
correlation, evidence, and opaque concurrency data from clients.

The feature adds no authentication, middleware, global exception formatting, or Host behavior.
Consumers select default or named read, author, review, publish, and retirement policies.
