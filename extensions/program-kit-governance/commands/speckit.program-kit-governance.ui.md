---
description: Adopt or safely generate a versioned UI experience, branding and discovery profile.
---

Read `references/ui-experience-v1.md`, its two JSON schemas, and `ui-evidence-v1.json` completely.
Read the consumer's accepted bootstrap decisions and current feature plan. `$ARGUMENTS` supplies
the requested UI choices or generation action. This command does not approve new architecture,
tracking, remote downloads, deployment, or publication.

For planning, select independent archetype/navigation/density/brand/CSS/page-intent dimensions and
record their source and override. Adopt existing accepted frontend and secure-web choices. Use
Lucide as the default icon family; consumers can supply licensed custom SVGs from another library.
Offer optional SVG logo content or a logo URL with alt text. Never require a logo to bootstrap.
Gather consequential branding choices; use safe defaults for omitted ordinary preferences.

For authorized first-code work, use `scripts/ui_profile.py init --target .` only if both source
files are absent, then edit the consumer-owned `.program-kit/ui/profile.json` and `content.json`.
Use `validate`, `build`, then `check`. Never use init to replace existing inputs, bypass generation
conflicts, or publish sample content. Port generated head fragments and semantic token variables
into an accepted SSR/SSG framework through an explicit adapter; native HTML is a working default
reference renderer. Preserve one initial-response metadata owner. Keep custom CSS in the consumer
layer and keep private content out of the public projection.

Run the generated pinned `acceptance/tests` suite using the approved exact Node/npm toolchain and
scripts-disabled npm restore. Capture the real-browser evidence and require the actual consumer
journey and deployment/manual checks listed in the profile before claiming product acceptance.
For .NET, enable `ProgramKit.Web.Discovery` only in an appropriate public root shell if this feature
owns those routes; do not modify ProgramKit.Host or duplicate another framework's routes.

Report source/generated paths, passed evidence, unresolved consumer adapter/manual/deployment
checks, and exactly which assumptions were adopted. Never claim universal psychological response,
AI discoverability, ranking improvement, consent-law compliance, or WCAG certification from this suite.
