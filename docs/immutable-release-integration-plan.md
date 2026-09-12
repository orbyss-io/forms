# Verified immutable release integration plan

Issue: [orbyss-io/forms#1](https://github.com/orbyss-io/forms/issues/1)

Status: implemented in source following the agreed 2026-09-12 plan. See [the integration guide](immutable-release-integration.md) for the implemented API, adoption boundary and evidence. Local verification is recorded there; publication and consumer migration have not been performed. The full release browser gate remains required.

## Outcome and ownership

Deliver an executable, supported build-time producer → synthetic published release → admission → `prepareJsonFormsRuntime` → `OrbyssJsonForms` reference, with regression evidence and an adoption checklist. Include focused Forms fixes needed to make the entire journey work.

The calculator is a reference application. No calculator fields, quantity policies, pricing, branch-specific cleanup rules, Calculate/Reset buttons, fixed language set, or product authorization rules become library defaults. Forms continues to own generic form definitions, validation, release integrity, renderer/action contracts and framework-neutral runtime mechanisms. Applications own renderers, interaction policies, pricing, authorization and durable business operations.

Use the existing package family. Keep .NET projects directly under `src/` or `tests/`, TypeScript under `src/typescript`, and orchestration under `scripts/`. Dependencies remain released Foundation packages and, where needed, released Localization abstractions. No Program Kit or Localization implementation source dependencies.

Consumer migration, live management in RM-01, approval/workflow redesign, bootstrap, paid agent tests, tagging and publication remain outside this work. Existing management transitions are exercised by the synthetic build producer without changing their approval semantics.

## Accepted decisions

- Produce a complete working reference, including focused library changes when necessary.
- Bundle release artifacts and the expected release manifest in one trusted application deployment. Hash checks establish integrity against that trusted expectation; they are not publisher signatures.
- Add reusable admission to the existing contracts/runtime packages and preserve the existing preparation API.
- Support authored visibility and enablement conditions together, authored field read-only state, and host-wide read-only state. Read-only takes precedence over enabled.
- Add explicit conditional requiredness to the provider-neutral model, generated JSON Schema and .NET validation. Visibility, enablement and read-only never implicitly change validity.
- Reference policy: changing a branch removes obsolete branch answers and dependent results; ordinary Back preserves answers. The cleanup policy is application code, separate from generic schema validation.
- Reference policy: Cancel calculation preserves answers and suppresses late results; Reset clears the journey. Changed inputs invalidate pending calculations. The synthetic handler performs no durable operation.
- Reference policy: retirement knowledge comes from the trusted deployment snapshot. Reject a release marked retired or excluded by that snapshot. Active journeys remain pinned; no claim of immediate retirement enforcement across deployments.
- Reference locales are `en`, `nl`, `de`, `ar`, with complete labels, choices, help, navigation, actions, validation and public failures, plus RTL evidence. Completeness is reference acceptance policy, not a fixed Forms language list or a removal of generic fallback support.

## Accepted condition semantics

The user accepted the following bounded semantics for new authored conditions:

1. Start with one typed scalar comparison against one declared field: equals, not-equals, present or absent. Support strings, booleans and finite numbers. Reject incompatible comparison values at authoring validation. Defer compound AND/OR trees, expressions, computed values and array traversal. Share these explicit semantics between new validation and UI conditions.
2. Missing or null discriminator values make equality and inequality false; an explicit absence condition is true. Presence means the property exists and is non-null. Empty string, zero and false are present; existing value constraints govern whether they are valid. Wrong-type values produce normal validation errors and do not satisfy typed comparisons. Preserve existing unconditional requiredness and draft-validation behavior.

Implementation must not silently reinterpret existing serialized visibility rules or old release artifacts. Keep the legacy contract/path compatible, and express new typed behavior explicitly. Preserve unconditional `Required` behavior. For new authoring, reject simultaneous unconditional and conditional required declarations so the author must state one intent.

## Existing evidence and gaps

| Area | Existing support | Work needed |
| --- | --- | --- |
| Publication | `DefaultFormCatalogService` and Management probe exercise review, approval and publication | Build a reusable producer recipe through those public APIs |
| Runtime | Preparation checks schema hashes, bounds, retirement and registry requirements | Bind the expected form/release/revision and every artifact before preparation |
| Candidate digest | Covers schemas and requirement manifests | Does not by itself bind release identity, locale values or generated validator |
| Browser | Fixture-owned React renderers and browser suite | Current fixture handwrites schemas and directly constructs runtime |
| Cross-language fixture | .NET-emitted release reaches TypeScript preparation | Current fixture is directly constructed rather than catalog-published |
| Conditions | Compiler emits SHOW; required fields are unconditional | Add generic editability/composition and explicit conditional-required parity |
| Actions/wizard | Existing hooks, controllers, abort and navigation | Compose application-owned cleanup and stale-result suppression |

Baseline source version is `0.1.1`. Its [Release workflow succeeded](https://github.com/orbyss-io/forms/actions/runs/34216590522), including NuGet propagation verification and npm publication. This establishes publication evidence for that baseline, not availability of the capabilities planned here. A fresh registry installation was not verified during planning.

## Implementation sequence

### 1. Define generic condition contracts and compatibility

Update `src/Orbyss.Forms.Abstractions`, definition validation in `src/Orbyss.Forms.JsonForms`, and any cross-language contract representation needed for the new fields.

- Add explicit conditional-required and enablement contracts plus field read-only metadata. Use a bounded, provider-neutral condition representation; proposed API names such as `RequiredWhen` are descriptive until the public API review.
- Validate referenced field identities, comparison types, supported paths and conflicting authoring intent.
- Preserve old definitions and artifacts. Keep new optional metadata from silently changing old published content or candidate-hash interpretation.
- Update `DefaultFormCompatibilityAnalyzer`: new or changed required conditions may tighten accepted data and must be classified conservatively. Cover old/new definition comparison and serialization compatibility.

### 2. Compile and validate the same semantics

Update `JsonFormsCompiler`, `DefaultFormDataValidator`, and the framework-neutral runtime where UI condition handling requires it.

- Compile conditional requiredness into standard JSON Schema `allOf` / `if` / `then`. Equality/inequality predicates must require the discriminator path explicitly; absence predicates deliberately test absence. Required nested targets must also require the necessary object ancestors.
- Evaluate the same condition against immutable candidate field metadata on the server, without a dependency on the UI layout or JSON Forms implementation. Preserve draft mode's existing treatment of missing required values; enforce conditional requiredness on submission.
- Use AJV's existing build-time standalone generation for root validation. Do not introduce browser code compilation or a general expression interpreter.
- Compose visibility and enablement deterministically despite JSON Forms' single-rule-per-element representation. Prefer supported compiler-generated layout/control composition; preserve field identity, translations, renderer allowlists and accessible structure. Document and test the resulting renderer contract. If this cannot preserve the accepted semantics through current extension points, surface that precise capability gap before selecting a broader runtime architecture.
- Keep React thin. Assess and use `onChange`, `readonly`, runtime context and existing action APIs before proposing any facade extension.

### 3. Produce the immutable fixture through publication

Add a deterministic reference producer project directly under `tests/`, with repository orchestration under `scripts/`. Its documented recipe uses public Forms packages/APIs and can be reproduced outside the repository.

- Define the synthetic form using Forms definitions, including explicit conditions and allowlisted renderer/action requirements.
- Exercise the real catalog compile/review/approve/publish lifecycle with synthetic actors/evidence and controlled test inputs. Do not construct the accepted fixture with `new FormRelease` or assemble schemas at request time.
- Export exact release bytes, locale artifacts and build metadata. Make nondeterministic IDs/time explicit inputs or normalize only documented build metadata, so regeneration has a meaningful drift check.
- Generate the standalone validator from that exact published data schema with the pinned toolchain. Produce a deployment binding manifest covering form/release/revision, complete release bytes, locale bytes, validator artifact and requirement manifests, with explicit format/version and encoding rules.
- Keep the publication candidate hash's existing meaning. The broader deployment binding supplements it; it does not relabel it as complete provenance.

### 4. Add reusable admission and deployment binding

Place serializable binding contracts in `forms-contracts` and an additive admission function in `forms-jsonforms-runtime`.

- Accept a separately trusted expected manifest and bounded release/artifact input. Validate shape and resource limits before accessing nested metadata.
- Verify exact expected identity and bound artifact bytes, retirement snapshot, complete requirement metadata and existing candidate/artifact invariants. Bind the entire authoritative release, including `Candidate.Fields` consumed by .NET validation, so server and browser cannot select different contracts. Reject altered or valid-but-foreign inputs before rendering or action dispatch.
- Use an explicit byte representation for digest verification; do not rely on unspecified cross-language JSON reserialization. Defensively snapshot both trusted expectations and admitted data to prevent mutation after admission.
- Bind locale selection to the admitted dictionaries. Generate and verify the validator module during the trusted build, then import it statically from the application bundle. An arbitrary JavaScript callback cannot prove its own provenance. Never evaluate validator source or import an executable URL supplied by the release.
- Connect admitted releases to existing preparation without breaking callers. A typed admitted result guides composition; it does not replace runtime checks or establish trust in a compromised host.
- The expected manifest is shipped through the application's trusted deployment. Replacing an input release and recomputing its self-reported hashes cannot change the pinned expectation.

### 5. Connect the reference application

Extend `src/typescript/tests/forms-browser` to consume the producer output through admission and preparation. Retain useful focused tests while replacing the acceptance path that bypasses the intended journey.

- Render with fixture-owned React renderers through `OrbyssJsonForms`.
- Demonstrate combined visibility/editability, field read-only and host review mode, explicit conditional validation, and ordinary backtracking.
- Keep branch cleanup and dependent-result invalidation in the example's state policy. Apply explicit schema validation to the resulting data; avoid special completeness checks hidden inside Calculate.
- Compose the existing allowlisted action controller with a fake product handler. Prove cancellation, changed-input races, reset, late completion and rejection of undeclared actions.
- Exercise all four sample locales and RTL. Other languages remain valid consumer choices.
- Prevent arbitrary scripts and external schema references; verify the selected registries are the ones actually passed into preparation/rendering. Ship no production renderer library or product pricing service.

### 6. Prove the contract through regression and packaging

Use shared generated vectors for .NET validation, AJV build output and browser standalone validation. Cover true/false/missing/null/wrong-type discriminators, present/absent/empty targets, nested paths, draft/submission modes, an unchanged published-baseline `0.1.1` fixture, combined UI conditions including ancestor/global state, and schema determinism. Fail unsupported UI combinations explicitly rather than silently dropping a condition.

Admission negatives include foreign form/release/revision, altered content with unchanged hashes, self-consistently rehashed content differing from the trusted manifest, mixed validator or locale revisions, altered renderer/action metadata, retirement metadata changes, malformed or oversized input, unknown renderer/action identifiers, unsafe UI content and external references. Assert rejection before rendering/action invocation, not only that some later exception occurs.

Add browser acceptance for the complete producer-to-renderer journey on Chromium, Firefox and WebKit. Cover action races, branch cleanup, explicit validation, localized errors and RTL. Verify the built application works under the existing no-dynamic-code restrictions.

Exercise packed packages from an isolated consumer, including the new public admission and condition contracts. Repository-relative source imports cannot be the adoption recipe. Retain current package-count and dependency-isolation checks.

Wire new producer drift/parity and admission/reference checks into the existing CI and Release workflows without weakening gates. Relevant existing commands from the repository root:

```powershell
dotnet restore Orbyss.Forms.slnx --locked-mode --configfile NuGet.config
dotnet build Orbyss.Forms.slnx -c Release --no-restore
python tests/validate_forms_management.py
python tests/validate_forms_operations.py
python tests/validate_forms_localization_contracts.py
python tests/validate_inmemory_storage.py
python tests/validate_package_retirement.py
python tests/validate_forms_frontend_ci.py
python tests/validate_frontend_publication.py
python tests/validate_forms_frontend.py --install
python tests/validate_forms_frontend_packages.py
python tests/validate_forms_physical_acceptance.py
python tests/validate_forms_browser.py --install-browser --engines chromium,firefox,webkit
dotnet pack Orbyss.Forms.slnx -c Release --no-build -p:PackageOutputPath=C:/Code/Orbyss/forms/artifacts/nuget
python tests/validate_package_metadata.py --packages artifacts/nuget
```

The frontend install wrapper performs locked `npm ci` and the npm build/tests. The package suite installs packed tarballs in an isolated consumer. Record any environment-specific failures accurately; passing a subset is not full browser acceptance. These commands are planned validation, not tests run during this interview.

### 7. Deliver adoption instructions and evidence

Document the public producer recipe, trusted deployment assumption, exact package versions actually tested, binding format, supported admission/preparation sequence, static validator import, registry setup, locale setup, consumer policy boundaries and retirement limitation.

Provide a requirement-to-test evidence table and commands to regenerate the synthetic artifacts and reproduce the reference. Identify changed-package requirements precisely. A local packed-package pass proves implementation compatibility; it does not prove public availability.

The implementation is reviewable when every agreed behavior has passing regression evidence and the adoption recipe works against packed artifacts. Consumer adoption of changed packages remains blocked until a separately authorized complete Release workflow succeeds and package availability is verified. Do not tag, publish, migrate RM-01 or imply that merging this work publishes it.

## Reference material

- [JSON Schema conditional validation](https://json-schema.org/understanding-json-schema/reference/conditionals): explicit conditional data constraints.
- [JSON Forms rules](https://jsonforms.io/docs/uischema/rules/): SHOW/HIDE and ENABLE/DISABLE UI effects.
- [JSON Forms middleware](https://jsonforms.io/docs/middleware/): capability to assess, not an assumed Orbyss React prop.
- [JSON Forms custom renderers](https://jsonforms.io/docs/tutorial/custom-renderers/): application-owned renderer integration.
