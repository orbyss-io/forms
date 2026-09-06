# Default adoption

## Bootstrap promise

Program Kit produces a complete, opinionated, usable baseline. Human attention is reserved for
deviations, material acknowledgements, and consequential decisions that cannot be answered safely
from the confirmed bootstrap intake or the selected Program Kit profile.

The absence of an explicit project choice is not a reason to leave an ordinary engineering choice
open when an applicable Program Kit default exists. Defaults are authoritative for the baseline but
remain easy to supersede through an explicit intake override or a later Accepted ADR.

## Decision precedence

Browser projects also adopt `ui-experience-v1`: independent brand/layout/CSS/page intent, optional
SVG logo and default Lucide icons, WCAG 2.2 AA target, initial-render public metadata, private export
exclusion, and no default analytics. These are reviewed baseline defaults, not new host middleware
or a forced frontend framework. Override through the normal decision register.

Classify every bootstrap choice by the first applicable source:

1. **Explicit intake**: direct project intent such as "use PostgreSQL" or "Keycloak is the initial
   identity provider". Adopt it; do not reopen it merely because implementation details remain.
2. **Explicit override**: intake or project configuration deliberately replaces a Program Kit
   default. Record the default, override, reason, and affected evidence.
3. **Program Kit default**: apply the selected versioned profile when intake is silent.
4. **Derived default**: apply a low-risk consequence of accepted project shape and guardrails,
   recording the rationale and override path.
5. **Genuinely unresolved**: require human input only when business, legal, regulatory, security,
   financial, tenancy, production, or recovery context makes a safe default inappropriate.
6. **Deferred until triggered**: record decisions that are not yet material. They do not block
   unrelated specifications or implementation.

Words expressing commitment in confirmed intake evidence (`must`, `uses`, `is`, `will`, `initial shape`)
are explicit intent. Examples, alternatives, future directions, and phrases such as `evaluate`,
`such as`, or `for example` remain candidates.

## Adoption evidence

Write `docs/architecture/bootstrap-decisions.json` using schema version `1.0`. It records the
versioned default profile, selected profiles, adopted choices and their sources, overrides,
material acknowledgements, genuinely unresolved decisions, and deferred decisions. Every adopted
choice includes a stable ID, decision, rationale, and easy override path.

The assessment human gate approves the exact hash of the assessment, tooling evaluation, decision
backlog, decision register, and concise review packet. Architecture may then treat explicit intake,
Program Kit defaults, and derived defaults as accepted bootstrap authority under the ratified
constitution. Consolidate them in `docs/architecture/decisions/bootstrap-baseline.md`; do not create
one approval chore per ordinary default.

Project-specific choices outside that reviewed baseline still require the normal ADR process.

## Managed toolchain precedence

Selected Program Kit technology profiles supply exact toolchain and package pins through their
managed manifests. Those pins are baseline authority before current-version research and before
probing the local environment. Research verifies compatibility and maintenance; it does not replace
a managed pin with a current candidate. A missing or older local installation is a remediation
requirement: clearly urge the user to install or upgrade to the exact managed version, side-by-side
where the ecosystem supports it.

Only an explicit user decision may retain a different locally installed .NET SDK as project truth.
Record that exception in `bootstrap-decisions.json.toolchain` with source `override`, a non-empty
reason, and an override entry whose ID is `managed-toolchain-version`. Ordinary managed pins use
source `program-kit-default`, exactly match the selected profile manifests, and need no separate ADR.

When Node remediation is approved but no supported manager is present, stop with an actionable
manager-install instruction rather than choosing or installing one implicitly. On Windows, prefer
the official per-user `fnm` routes (WinGet, Scoop, or the release binary); do not send a
non-administrator shell into an elevation-bound Chocolatey install. After `fnm install`, verify the
pin in the same process with `fnm exec --using=<version> node --version`; parent-shell PATH or profile
activation is not valid immediate verification evidence.

## .NET default

When .NET is selected, the external application-neutral `ProgramKit.Host` and runnable-host release model are the
automatic runtime default. Consumer repositories create packable feature projects and activation,
configuration, package-closure, and release evidence—not a custom `.Host` project or application
`Program.cs`. Adopt this model unless the confirmed bootstrap intake explicitly opts out. An opt-out records the alternate
host, reason, consequences, and affected managed baseline.

The standard runtime currently introduces pinned Program Kit, CShells, and Nuplane preview packages
and the configured preview package sources. The assessment review packet must disclose that material
supply-chain fact. Approving the assessment records the human acknowledgement; it does not download
packages or run restore. Repository synchronization and networked restore remain separate actions.

## Secure browser default

When a browser UI and authenticated HTTP boundary are detected, adopt the Program Kit
`bff-cookie-v1` secure web profile unless explicit intake or an Accepted ADR selects another
deployment shape. “SPA” describes the client UI and does not by itself select browser-held bearer
tokens. The same-origin BFF remains the default for React and other SPA frontends.

Select `spa-pkce-v1` only for an independently hosted static client that must call APIs directly, or
when an explicit decision accepts browser token exposure and the profile's renewal, storage, CORS,
and logout consequences. Record the profile and version in the bootstrap decision register. Feature
specifications inherit the chosen profile and must not reopen its ordinary implementation details.

Every authenticated browser adoption also inherits threat model
`program-kit-web-threat-model-v1` and evidence profile
`program-kit-web-security-evidence-v1`. These own the attacker model, source authority/status,
control traceability, configurable-default rationale, residual risks, assurance levels, and review
triggers. A consumer records only its additions and overrides; an override is incomplete without an
owner, affected control/default, evidence, review condition, and regression test.

## Proportional decisions

Do not turn every valid question into an ADR or bootstrap blocker. Close ordinary details through
the applicable default, feature specification, acceptance criteria, or deterministic test. Defer
production topology, workload objectives, legal retention, and recovery objectives until their
lifecycle gates when they do not block the first vertical slice.
