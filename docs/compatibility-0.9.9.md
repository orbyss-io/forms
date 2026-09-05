# Program Kit 0.9.9 compatibility report

0.9.9 is an additive feature and security-boundary release over 0.9.8. Program Kit components advance
to `0.9.9`; runtime packages and the host image advance to `0.9.9-preview.1` because runtime sources
changed and new identity packages are published.

Existing BFF and SPA-PKCE selections remain source compatible. Web middleware and default Problem
Details behavior are now independently composed CShell features, so a consumer override can disable
the default response feature and supply its own. New authentication and identity-administration
capabilities are opt-in and do not activate merely because their NuGet package is available.

The identity-administration abstractions are provider-neutral. The Keycloak adapter exposes portable
interfaces for common business orchestration and explicitly provider-named interfaces for flows,
external providers, organizations, and realm operations. No `InternalsVisibleTo` access is used.

Existing consumers should upgrade the full Program Kit bundle sequentially and rerun their managed
profile synchronization. Changed runtime pins require the normal lock-renewal and verification workflow.
