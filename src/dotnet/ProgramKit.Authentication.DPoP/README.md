# ProgramKit.Authentication.DPoP

Provider-neutral RFC 9449 resource-server enforcement packaged as a CShells middleware feature for
the SPA-PKCE bearer profile. It validates ES256 proof signatures, public JWK thumbprint binding,
HTTP method and public target URI, access-token hash, proof age, and per-proof replay uniqueness.
DPoP-bound tokens cannot fall back to bearer use, and required deployments reject unbound tokens.

The default replay store is atomic within one process. Multi-instance resource servers must replace
`IDPoPReplayStore` with a shared implementation whose reservation operation is atomic across all
instances; the public contract makes that deployment requirement explicit without coupling the
feature to a particular cache or database.

Set `RequireNonce` when a resource server should challenge clients with a single-use `DPoP-Nonce`.
`IDPoPNonceStore` is replaceable for the same clustered-deployment reason; missing, expired, or
consumed nonces fail with `use_dpop_nonce` and receive a fresh challenge header.

Outbound clients use `ECDsaDPoPProofGenerator` with either a new ephemeral P-256 key or imported
PKCS#8 key material. The generator owns its key, exposes its binding thumbprint, removes query and
fragment from `htu`, and emits `ath` and a server nonce when supplied. Persisted private-key bytes
remain consumer-owned secret material and must be protected at rest.

The public origin is explicit so reverse-proxy headers cannot redefine proof targets. The feature
does not contain identity-provider product logic; provider adapters enable DPoP-bound token issuance.
