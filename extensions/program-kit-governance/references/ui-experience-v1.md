# UI experience v1

Adopt when a browser UI is in scope; omit for non-UI projects. Record choice ID
`ui-experience-profile` with source, rationale and override in bootstrap-decisions.json, include
`ui-experience-v1` in selected_profiles, and record the independent branding/layout/discovery
choices. Do not reopen standard defaults as repeated approval questions. Intake records intent;
first-code generates the files. Existing frontend and authentication decisions retain authority.

The consumer owns `.program-kit/ui/profile.json` and `content.json`. Start with:

```powershell
python .specify/extensions/program-kit-governance/scripts/ui_profile.py init --target .
python .specify/extensions/program-kit-governance/scripts/ui_profile.py build --target .
python .specify/extensions/program-kit-governance/scripts/ui_profile.py check --target .
```

`init` never replaces existing inputs. Review the sample origin/content before deployment.
`build` generates only beneath `web/generated/program-kit` and records hashes outside the public
output. It refuses edited/untracked conflicting outputs and path traversal/symlink targets.
`check` is the deterministic consumer CI drift gate. Edit sources or override CSS, not generated
files. All generated assets must be deployed as one coherent build; stale files must not remain.

## Independent choices

| Dimension | Choices / default |
| --- | --- |
| Archetype | journey, product-shell (default), workspace, content-hub, showcase |
| Navigation | sidebar (default), top, contextual, none |
| Density | comfortable (default), compact |
| Brand | name, primary/secondary seeds, optional semantic overrides per light/dark mode, font stack, font license, logo/favicon URLs and alt text |
| Character | quiet, balanced (default), expressive; shape square/rounded/pill |
| Scheme / motion | system (default), light, dark; subtle (default), expressive; always honor reduced motion |
| CSS adapter | native (default), tailwind, existing-system |
| Page intent | private-app, public-utility, public-landing, public-content |
| Analytics | none (default), explicit consent-gated adapter; never implicit tracking |

### Logos and icons

Branding can start without artwork. A logo accepts exactly one `url` or `svg` plus meaningful
`alt` text. Example (inside `brand`):

```json
"logo": {"alt":"Acme","svg":"<svg viewBox=\"0 0 32 32\"><path fill=\"#2457A7\" d=\"M16 0 32 32H0Z\"/></svg>"},
"icons": {"bundle":"lucide"}
```

SVG content is parsed and validated before generation, not injected as trusted arbitrary markup.
Supported shapes/groups/gradients/local clipping keep vector branding practical. Scripts, event
handlers, style elements/attributes, foreignObject, external references, embedded images, entities,
animation and linked use elements are rejected. Export text to paths and flatten unsupported
effects, or provide an approved separately hosted image URL. This deliberately conservative subset
is not a general SVG editor. Logos become `<img alt>` assets; decorative inline icons use
`aria-hidden`, while icon-only controls require an accessible name on the control. Color is not
the only state cue. Mirror directional icons only when their meaning reverses in RTL; never mirror
logos, check marks, clocks or other nondirectional symbols automatically.

| Family | Why choose it | License / integration |
| --- | --- | --- |
| Lucide (default) | Consistent outline vocabulary and framework-neutral SVGs | ISC plus MIT for Feather-derived assets; seven pinned starter icons included with notices |
| Heroicons | Good fit for a Tailwind-oriented visual language | MIT; import the used SVG subset as custom assets |
| Material Symbols | Fit with an existing Material product system and variable styles | Apache 2.0; import the used SVG subset, no remote icon font required |
| Phosphor | Multiple weights and a distinctive visual family | MIT; review/pin upstream assets before custom import |
| Font Awesome | Existing ecosystem or specialized/brand icon requirements | Free/pro licensing differs by asset format; review the exact license, do not assume all assets are MIT |
| Consumer artwork | Brand-specific symbols or an existing design system | Record source and actual rights; same SVG safety/semantics contract |

Use `icons: {"bundle":"custom","source":"...","license":"...","assets":{"search":"<svg ...>...</svg>"}}`
for another family or your own icons, or `bundle: none`. Include only used icons, maintain a
consistent stroke/size/weight system, and retain attribution notices in the deployed assets.
The renderer's `ui_svg.icon_markup` helper inserts validated inline SVG with inheritable color;
frontend adapters should consume the sanitized SVGs with equivalent semantics. An SVG loaded via
`img` does not inherit the parent's currentColor, so test its contrast separately.

Lucide is a pragmatic default, not a proven global popularity winner. npm's 2026-08-23–2026-08-29
download snapshot, retrieved 2026-09-05, was 97,818,518 for lucide-react, 4,109,387 for
@heroicons/react, 3,435,411 for @phosphor-icons/react, and 2,314,737 for @fortawesome/react-fontawesome.
These count package downloads (including automation), not people, websites or all ecosystem usage.
See `ui-icons-evidence.json` for source endpoints and the pinned vendored SVG revision.

Journey is focused progress/forms; product-shell is navigation plus canvas; workspace emphasizes
data and filters; content-hub emphasizes readable content and contextual navigation; showcase is
public narrative. Commerce composes content and journey; it is not a separate universal layout.
Adapt the examples to the actual first user outcome, not a mechanical authentication demo.

Tokens use the DTCG 2025.10 color representation, primitive-to-semantic aliases, CSS custom
properties, and component/layout styles. Tailwind's generated `@theme inline` bridge maps those
same variables. The generated `integration/tailwind-entry.css` declares the cascade order before
imports so Tailwind Preflight cannot reset the native components; add explicit application
`@source` paths there. Use the isolated pinned Tailwind 4.3.3 compatibility graph or a reviewed
compatible consumer toolchain. Merely appending the bridge to an arbitrary layer order is unsafe.
Existing design systems consume `tokens.json`/`tokens.css` through an explicit mapping. Native HTML
is the executable reference renderer, not a mandate to replace an accepted React/Vue/etc stack.
For other SSR/SSG frameworks, consume generated head fragments/content contracts in the initial
response, preserve one canonical head owner, and run the same acceptance suite against the real
adapter. Client-only metadata updates do not satisfy public-content acceptance.

Multi-device support is mandatory for every browser UI. Layouts must reflow without unexpected
page-level horizontal overflow on phone, tablet and desktop viewports; support touch, keyboard and
pointer input; tolerate portrait/landscape changes and virtual-keyboard viewport reduction; use
content-driven sizing rather than fixed device assumptions; and preserve focus, reading order,
meaning and available actions at enlarged text. Core acceptance covers Chromium, Firefox and WebKit
with representative touch phone/tablet profiles. Emulation is deterministic compatibility evidence,
not a substitute for representative physical-device and assistive-technology journey acceptance.

Generated Keycloak brand CSS and email color values are bridge assets, not replacement login or
email templates. Explicitly integrate them with the existing consumer-owned Keycloak theme and
rerun its provider/browser/mail suite. Do not modify upstream identity flows or assume email
clients support CSS variables. Font files and logos remain consumer-owned; no remote fetch occurs.

## Discovery and analytics

Public visible content is the source of metadata, structured facts, and optional Markdown. Content
blocks are plain text, links, lists and real tables, never trusted arbitrary HTML. Article/product
facts appear visibly as well as in JSON-LD. Canonical URLs are stable HTTPS URLs on the configured
origin. Translations must reference existing public, indexed reciprocal alternatives.
`lastModified` is an editorial date, not the build time. Nonindexed and private pages are excluded
from sitemap/Markdown/llms; private bodies and private routes are absent from public artifacts.
Private application routes must enforce authentication in their own feature; noindex/robots are
not access controls. Do not deploy private source JSON or the generation state.

Crawler search/training/user-fetch preferences are separate and have provider-specific semantics.
Read the evidence register before deployment; robots compliance is not universal and user-initiated
fetchers differ. Do not claim a User-Agent proves crawler identity. WAF/IP verification belongs to
deployment assurance. llms.txt and Markdown are optional community conventions, not universal
discovery requirements. No special AI schema or ranking guarantee is claimed.

Analytics is a separate adapter. The default sends nothing. Events contain only approved constant
page/event identifiers, never raw URL/query/title/account/email/token data. Basic consent gating
means no provider call before consent; no advanced cookieless collection is silently enabled.
Disable automatic SPA page views if using the provided navigation tracker; one navigation owns
one page view. Revocation stops subsequent sends; already sent data cannot be recalled by the SDK.

`public/assets/analytics.mjs` exposes the provider-neutral consent/navigation controller and a GA4
adapter. GA4's transport loader/unloader is explicitly consumer-owned: activate it only after
consent, disable enhanced-measurement history page views in the property, and verify the actual
network behavior in deployment. The adapter suppresses automatic config page views and sends a
constant placeholder location/empty title plus approved page IDs instead of browser URL/title.
Do not claim the injected-transport tests prove Google's network, consent-law compliance or deletion
of previously collected data. Another provider implements the same activate/deactivate/send contract.

Select `analytics: {"provider":"none"}` (default), `{"provider":"custom","events":["journey_started"]}`,
or `{"provider":"ga4","measurementId":"G-YOURID","events":["journey_started"]}` in the profile.
Generated `integration/analytics.json` contains approved constant page/event IDs and the selected
adapter configuration. It deliberately does not auto-load a transport or start tracking; the
consumer binds its consent UI and navigation lifecycle to the controller. Private-route analytics,
if wanted, use explicit constant identifiers in the consumer rather than exporting private content.

Consumer browser acceptance after generation (exact Node 24.20.0/npm 11.19.0):

```powershell
Set-Location web/generated/program-kit/acceptance/tests
npm ci --ignore-scripts --no-audit --no-fund
npx --no-install playwright install chromium firefox webkit
npm test
```

Use the managed `js_toolchain.py` runner where installed to preserve exact runtime, cache and CA
trust. No `--force`, legacy peer resolution or disabled TLS validation is allowed. On Linux CI,
provision Playwright's system dependencies. Keep node_modules/browser evidence out of source control;
deploy only `public/` plus `publication.json` for the optional .NET feature, never acceptance files.
Optional comprehension experiments use `ui-evaluation-v1.md`; the scorer has no model/network calls.

The acceptance-only Tailwind compiler is not a production dependency for native/existing-system
consumers. Browser acceptance includes a real compiled light/dark semantic-style comparison, not
just a text assertion that a theme directive exists.

## Quality and evidence

First-code gates: token contrast, generated drift, semantic initial HTML and safe escaping,
private-export negative tests, canonical/language/sitemap consistency, honest content extraction,
keyboard dialog/focus behavior, state gallery, reduced motion, RTL, narrow/zoom-equivalent layouts,
automated accessibility and asset budgets. Do not treat a gallery as consumer task acceptance.
First-deployment gates: authenticated private routes, CSP fit, real screen reader and keyboard
journey, actual translations, content/editorial approval, real crawler/WAF fetch, consent/network
inspection, and production LCP/INP/CLS collection where approved. Lighthouse cannot certify field INP.

Evidence categories are normative standard, documented provider contract, bounded empirical
finding, implementation policy, or experimental convention. Evidence and caveats live in
`ui-evidence-v1.json`. Reevaluate standards/providers at profile upgrades and before deployments.
Use honest progress, familiar labels, related grouping, accessible targets, stable focus and clear
feedback. Never implement deceptive defaults, fabricated scarcity, invented statistics, universal
color-emotion rules, or arbitrary maximum menu counts as scientific requirements.
