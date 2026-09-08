# Orbyss.Forms.Submissions.Mcp.AspNetCore

An `IShellFeature` that explicitly contributes only `FormOperationsTools` to the shared stateless
Streamable HTTP transport from `Orbyss.Foundation.Mcp.AspNetCore`. It derives ownership from the transport
principal and does not map a second MCP endpoint.

The contributor installs no authentication, CORS, rate limiting, host filtering, exception
formatting, or middleware. The shared endpoint uses the host default or configured named policy;
the selected Orbyss Forms authentication profile owns scheme registration, token validation, and
authentication/authorization middleware. A canonical `permission:*` policy uses the mapping from
`Orbyss.Foundation.Authentication`. Bearer is the normal remote-client profile; BFF cookies require the
client to participate in the BFF antiforgery contract.
