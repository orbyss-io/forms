# UI experience implementation evidence

Implemented as an unpublished working-tree initiative on the authentication RC at `5eb362d`.
No tags, remote pushes, consumer task notifications, tracking activation or infrastructure changes
are part of this work. Existing release/version files are unchanged; local development archives
are verification artifacts, not permission to publish another candidate under an existing tag.

## Delivered boundary

- Versioned consumer profile and content schemas, `/speckit.program-kit-governance.ui`, bootstrap
  decision/toolchain authority and lifecycle instructions; no frontend stack is silently replaced.
- Five responsive archetypes with independent navigation/density/brand/CSS choices. DTCG color
  primitives/semantic/component aliases, light/dark/system CSS, contrast validation, focus,
  reduced motion, forced colors, RTL/reflow and state gallery.
- Optional SVG logo content or image URL; conservative SVG parser, local gradient/clip references,
  pinned Lucide starter icons and retained ISC/MIT notices; custom licensed icon families supported.
- Initial HTML/head, canonical/hreflang, Open Graph, visible Article/Product/SoftwareApplication
  facts plus matching JSON-LD, truthful sitemap dates, independent crawler groups, opt-in public
  Markdown/llms. Private bodies/routes never enter the generated public projection.
- Native CSS and a compiled Tailwind bridge with explicit cascade-layer order. Existing systems
  consume the same tokens; their framework-specific adapter remains consumer-owned.
- Independent consent-gated analytics controller and GA4 injected-transport adapter. No transport,
  automatic tracking or remote fonts are loaded by the default pages.
- Provider-neutral `ProgramKit.Web.Discovery.Abstractions` plus optional `ProgramKit.Web.Discovery`
  CShells feature. Exact public GET/HEAD allowlist; bounded, hash-verified files; no Host edits.
- Optional local multi-provider evaluation scorer, with lexical/citation metrics explicitly
  distinguished from factual entailment, ranking or universal model compatibility.

## Verification

`python tests/validate_ui_experience.py` covers 23 tests, including 90 archetype/CSS/density/scheme
combinations, token aliases/contrast, escaping, source consistency, private/nonindexed exports,
reciprocal locales, crawler choices, invalid URLs/paths, SVG attacks/licenses, generation conflicts,
stale-file removal, unowned public artifacts, bootstrap pin evidence, evaluation boundaries and the
mandatory cross-engine/phone/tablet/orientation acceptance contract.

`python tests/validate_ui_browser.py --install --install-browser` runs the locked acceptance graph:
Node 24.20.0, npm 11.19.0, Playwright 1.62.1, axe Playwright 4.13.0, Tailwind/CLI 4.3.3.
It checks four analytics contracts, Chromium/Firefox/WebKit desktop archetype/light-dark
combinations with axe, keyboard dialog/focus, reduced motion and RTL/enlarged-text reflow; Chromium
forced colors; Chromium touch-phone and WebKit touch-tablet portrait/landscape journeys; and real
compiled Tailwind/native semantic parity in both color schemes. Evidence and screenshots are preserved under
`artifacts/ui-browser/web/generated/program-kit/acceptance/browser-evidence/`; toolchain/lock hash
is in `artifacts/ui-browser/toolchain-evidence.json`.

On this Windows host, all 20 Chromium and all 20 WebKit engine/archetype/device combinations pass.
The complete command remains red because the pinned Playwright Firefox 153 bundle cannot start:
Windows SideBySide event 33 reports that its packaged `mozglue` assembly cannot be activated before
any Program Kit page is opened. The harness does not downgrade this to a skip. A Linux CI run or a
subsequent stable pinned Playwright graph must complete Firefox before multi-device hardening is
marked delivered.

Browser testing found and fixed dialog Tab wrapping, WebKit skip-link focusability,
narrow/enlarged-text button overflow, and Tailwind Preflight overriding native component styles
through an incorrect cascade-layer order.
Screenshots were visually inspected. They are evidence snapshots, not approved cross-platform
pixel-diff baselines.

`python tests/validate_web_discovery.py` starts a real loopback ASP.NET application through the
feature's public configuration/endpoint contracts. It verifies all 16 generated GET/HEAD routes,
body/content type/indexing headers, private/build-internal 404s, unsupported methods, hostile
manifest paths/types/hashes/visibility and consumer adapter replacement. No friend assemblies.

The deterministic `scripts/Test-ProgramKit.ps1` aggregate includes the UI tests and all existing
governance/authentication/local build-and-install regressions. The .NET solution is restored in
locked mode and built in Release; NuGet packing is verified separately under `artifacts/ui-nuget`.
CI and the release gate include the new UI/browser/public-discovery tests. These local results do
not claim that remote CI has run.

`python tests/validate_packaged_ui.py` extracts the built governance extension into a clean
consumer and executes its own init/validate/build/check entry point. It verifies that scripts,
schemas, templates, icons/licenses and the browser lockfile are usable without repository imports.

## Remaining consumer/deployment acceptance

An application still owns its real journey, accepted framework's initial-render integration,
actual logo/fonts/brand and translations, icon meaning/contrast, custom Keycloak-theme integration,
and provider analytics transport/property configuration. Test those against the profile rather
than treating the gallery or a stub transport as application acceptance. The Keycloak bridge emits
CSS and literal email colors; it does not rewrite existing identity/email templates.

Screen-reader task success, actual browser zoom, production CSP/authentication/WAF behavior, legal
consent requirements and field Core Web Vitals require appropriate human/deployment evidence.
No paid model or live bootstrap sessions were executed. Multi-provider scoring is tested with
synthetic trial documents; no real provider-comprehension or discoverability result is claimed.
