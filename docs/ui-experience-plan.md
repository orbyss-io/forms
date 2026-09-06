# UI experience and discoverability implementation

Status: initial implementation delivered; approved multi-device hardening is the next slice and is
tracked in `forms-localization-implementation-plan.md`. Final verification of the initial boundary
is recorded in `ui-experience-evidence.md`.
The authentication release candidate at `5eb362d` is unchanged in
history. This work is not a release or publication approval.

## Contract

Deliver `ui-experience-v1` as an opt-in, framework-neutral profile shipped with the governance
extension. A consumer owns its profile and content sources. Program Kit generates deterministic,
hash-tracked outputs and refuses to overwrite edits. Browser authentication remains an independent
secure-web profile. The first consumer slice must demonstrate a real branded user journey.

Separate archetype (journey, product-shell, workspace, content-hub, showcase), navigation, density,
brand, CSS adapter, accessibility, page intent, crawler policy, and analytics. Native CSS is the
dependency-free default. Tailwind and existing design systems consume the same semantic tokens;
no frontend framework is silently imposed. Public pages get initial HTML, not just client-side
head updates. Private page bodies are never emitted into public exports.

## Delivery sequence

- [x] Versioned profile/content contracts, evidence register, bootstrap/lifecycle integration.
- [x] Validated brand-to-token generation, responsive archetypes, component state gallery,
  light/dark/system, reduced motion, forced colors, RTL and keyboard behavior.
- [x] Safe initial HTML/head renderer, JSON-LD, canonical/locales, sitemap, crawler policies,
  optional Markdown/llms exports, separate consent-gated analytics adapters.
- [x] Optional `ProgramKit.Web.Discovery` CShells NuGet feature serving only validated public
  generated routes. No new Host middleware or privileged test assembly access.
- [x] Deterministic contract/security/upgrade tests, browser accessibility and interaction suite,
  measured asset budgets, local comprehension-evaluation contract and honest manual evidence.
- [x] Build/pack/install regression verification and usage/evidence handoff.
- [ ] Replace Chromium-only responsive approximation with the mandatory Chromium/Firefox/WebKit,
  phone/tablet/desktop, touch and orientation acceptance matrix before the Forms UI runtime ships.

## Acceptance boundaries

Core CI is offline/deterministic except explicitly provisioned build dependencies and browsers.
It does not call paid model APIs or perform live bootstrap. Multi-model retrieval/comprehension
evaluation is a separate consumer-invoked experiment, with provider/model/version, repeated trials,
answers and citations recorded. No generation claims guaranteed ranking or universal AI ingestion.
WCAG automated checks are not a certificate: screen-reader usability, task success, cultural brand
fit, and production Core Web Vitals still need human/field acceptance.

WebMCP remains an experimental action-interface follow-up, not a metadata requirement. Crawler
identities are versioned deployment guidance, not an authentication bypass or verified WAF identity.
No analytics, remote fonts, identity server configuration, publication, or infrastructure changes
are enabled implicitly.
