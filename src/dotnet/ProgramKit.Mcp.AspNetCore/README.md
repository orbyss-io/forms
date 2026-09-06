# ProgramKit.Mcp.AspNetCore

The single endpoint-only `CShells.IWebShellFeature` that owns Program Kit's stateless Streamable
HTTP transport. Independently selected bounded-context features contribute explicit closed-world
tool types to the same server. This avoids SDK-global tool registration accidentally creating
different endpoints with shared catalogs.

The endpoint is always protected by the host default or configured named policy. Authentication,
authorization middleware, CORS, host filtering, rate limiting, and error formatting remain owned
by selected host features. Bearer authentication is the normal remote-client composition.
