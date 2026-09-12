# Immutable release integration

This reference implements [Forms issue #1](https://github.com/orbyss-io/forms/issues/1): a public-API build producer publishes a synthetic release, the application admits its complete artifacts against a trusted deployment manifest, and `prepareJsonFormsRuntime` supplies the runtime for `OrbyssJsonForms`.

## Availability

These capabilities are introduced in Forms `0.2.0`, built on the repository's `0.1.1` baseline. They are **not part of the previously published 0.1.1 packages**. Isolated package tests use newly packed `0.2.0` artifacts; registry availability requires the tagged Release workflow to complete successfully.

The changed public packages are `Orbyss.Forms.Abstractions`, `Orbyss.Forms.JsonForms`, `Orbyss.Forms.Management`, `Orbyss.Forms.Submissions`, `@orbyss-io/forms-contracts` and `@orbyss-io/forms-jsonforms-runtime`. All 15 NuGet and 12 npm packages share version `0.2.0`. Foundation Analyzers and MCP ASP.NET Core are pinned to released `0.2.0`; Localization Abstractions remains `0.1.0`. Adoption requires a successful complete Release workflow and package availability verification. The existing React facade needs no new middleware prop.

The reference uses the repository pins: JSON Forms 3.8.0, React 19.2.8, Node 24.20.0 and npm 11.19.0. Consumer migration and live authoring deployment remain separate work.

## Produce once, consume the published artifacts

`tests/Orbyss.Forms.ReleaseIntegration.Probe/Program.cs` is the executable producer recipe. It uses only public Forms APIs:

1. Construct a provider-neutral `FormDefinition`, declaring fields, conditions and renderer/action requirements.
2. Create it with `DefaultFormCatalogService` and explicit mutation identity, actor and timestamp.
3. Submit that revision for review with synthetic fixture evidence, approve it with a reviewer, and publish it with a publisher.
4. Export the resulting `FormRelease`. The fixture retains its exact serialized UTF-8 release text, including `Candidate.Fields` for server validation.

The example's actors and evidence are test data, not a production approval policy. Its in-memory stores support deterministic builds without exposing management endpoints. Applications can compose other supported stores through the same public contracts.

After a locked restore and Release build, regenerate and verify the fixture:

```powershell
dotnet run --project tests/Orbyss.Forms.ReleaseIntegration.Probe -c Release --no-build --no-restore -- --output src/typescript/tests/fixtures/published-product.json
python tests/validate_forms_release_integration.py
```

The producer fixes actor identities, mutation timestamps and operation keys. Publication replay and fixture regeneration must reproduce the same bytes. Acceptance does not construct a release directly or compile schemas during a browser request. Existing focused legacy tests remain separate from this new publication journey.

## Author conditions explicitly

```csharp
var custom = new FormCondition(
    "kind",
    FormConditionOperator.Equals,
    JsonSerializer.SerializeToElement("custom"));

var detail = new FormFieldDefinition(
    "detail", "/detail", FormValueKind.String, false,
    new LocalizedTextReference("fields.detail", "Custom detail"),
    RequiredWhen: custom);

var control = new FormElementDefinition(
    "detail-control", FormElementKind.Control, [], FieldId: "detail",
    VisibleWhen: custom,
    EnabledWhen: new FormCondition("editable", FormConditionOperator.Equals,
        JsonSerializer.SerializeToElement(true)));
```

`RequiredWhen` controls validity. `VisibleWhen` and `EnabledWhen` control presentation. They may deliberately share a predicate, but none implies the others. `ReadOnly` is authored field metadata; the host may additionally set the facade's global `readonly` prop. These are UI editing controls, not authorization checks.

New conditions support one declared scalar field and equality, inequality, presence or absence. Equality uses typed string, boolean or finite numeric values without coercion. Missing/null values satisfy absence and fail equality/inequality. Empty strings, zero and false are present; ordinary constraints determine validity. Wrong-type values fail validation and typed equality/inequality. Compound expressions and array traversal are unsupported. Authoring rejects incompatible values, unknown field IDs and simultaneous unconditional/conditional requiredness.

The compiler emits standard JSON Schema `if`/`then` constraints under `allOf`. Predicates require discriminator ancestors explicitly; conditional target requirements require each object ancestor and the target property. .NET submission validation evaluates the same condition against the immutable field snapshot. Draft validation keeps its existing allowance for absent required values.

Adding or changing a required condition is conservatively classified as a breaking data-contract change. Legacy `FormVisibilityCondition` artifacts retain their original behavior; new typed semantics are opt-in and do not rewrite published releases.

## Compose UI rules without dropping constraints

JSON Forms permits one rule on an element. For a leaf with visibility and enablement, the compiler emits a visibility-controlled `VerticalLayout` around the original control carrying enablement. Containers retain their structural identity, including wizard Categories; their descendants carry the enablement predicates. All ancestor enablement conditions are conjoined on descendants because a child's own JSON Forms enable rule can otherwise override inherited disabled state.

Read-only controls retain read-only metadata without an overriding enable rule. Global read-only remains authoritative. Consumer layout renderers must honor `visible`, propagate `enabled` through `JsonFormsDispatch`, and handle the emitted layout types. Consumer controls must honor disabled/read-only state. The browser fixture demonstrates this contract; Forms does not ship a renderer library.

## Bind artifacts in a trusted application build

`src/typescript/tests/forms-browser/deployment.mjs` demonstrates the trusted build step. It generates the standalone validator from the exact published data schema and produces a format-version-1 `FormDeploymentManifest`:

- Expected form ID, release ID and revision.
- SHA-256 of the complete release JSON text, not just its schemas or `candidateSha256`.
- SHA-256 of each complete locale dictionary JSON text.
- Standalone validator source SHA-256 and its source schema SHA-256.
- The deployment's retirement snapshot.

Hashes operate on the exact UTF-8 text with no implicit reserialization or newline normalization during admission. The candidate digest keeps its existing compiler-defined meaning; full release binding additionally covers server fields, identity, publication metadata and all requirement manifests.

The build verifies the generated validator source and statically bundles it. The reference build attaches a generated binding export to that module; the source digest refers to the standalone source before that metadata export is appended. The application imports the function and binding together. It must not copy the expected manifest's hash onto an unrelated callback. No validator source or executable URL is loaded from release data.

Runtime JavaScript cannot prove an arbitrary callback's provenance. The trusted build and deployment establish the executable binding; admission detects mismatched binding metadata and rejects mismatched release or locale bytes. This is integrity relative to an application-deployed expectation, not cryptographic publisher authentication. A party able to replace the application and its trusted manifest is outside this boundary. No signing or key infrastructure is introduced.

## Admit, prepare, render

```typescript
// staticallyBundledValidator includes the trusted build's source/schema binding and
// an OrbyssValidator adapter over its statically imported standalone function.
const admitted = await admitFormRelease(
  releaseJson, localeJsonByTag, trustedManifest, staticallyBundledValidator);

const runtime = await prepareJsonFormsRuntime(
  admitted.release,
  installedRendererRegistry,
  installedActionRegistry,
  admitted.validate,
  createJsonFormsTranslator(admitted.translations[locale]));

// Pass the corresponding application-owned JSON Forms renderer entries to the facade.
// <OrbyssJsonForms runtime={runtime} data={data} renderers={entries} onChange={onChange} />
```

Admission snapshots mutable inputs before asynchronous verification. It checks bounds, shapes, exact identity, whole-release and locale digests, validator binding, required translations, retirement and candidate diagnostics. The admitted release/dictionaries and prepared schemas are immutable snapshots. Preparation enforces installed renderer/action requirements and rejects unsafe UI keys and external references, including references in rule schemas. An unknown UI element cannot evade the allowlist by omitting its ID.

Keep registry entries and renderer components under trusted application control. Unknown actions are rejected before dispatch. The expected manifest comes from the application deployment, not from the same untrusted input that supplies a claimed digest.

## Reference policies stay in the application

The configurable-product form is synthetic. Its fields, fake calculation, branch cleanup, four locales, Calculate/Reset buttons and review screen are not library defaults. The host removes obsolete branch answers and dependent results when the branch changes; ordinary Back preserves answers. Required branch data is enforced by the explicit schema condition, not a hidden Calculate check.

The action controller and wizard controller are existing Forms mechanisms. The application-owned controls pass edits to a host callback, which applies the edit and branch cleanup atomically to one authoritative application state. The host supplies that state through the facade's existing `data` prop; delayed engine notifications do not write back over newer input. Calculation reads the same current state. The renderer controls when computed validation messages become visible. Generation checks and cancellation prevent late results from restoring invalidated data; reset supplies fresh data and a fresh form instance. Cancel preserves answers; Reset clears the journey. The deliberately late fake handler has no durable effects. Real pricing, quantity policy, authorization and durable submissions remain product-owned.

The four example locales are English, Dutch, German and Arabic. Dictionary completeness is required for this reference; Forms retains generic language selection and fallback support. The shared translator adapter maps JSON Forms `.label` probes to compiler-declared base label keys while preserving missing-error signals.

Retirement is evaluated against the trusted deployment snapshot. Retired or excluded releases cannot start a new admitted journey. An active journey remains pinned. Immediate retirement enforcement without redeployment requires a separate authoritative lifecycle/freshness integration; this reference does not claim that behavior.

## Adoption and evidence checklist

- Generate through the public catalog lifecycle and review the exported release/fixture drift.
- Generate the validator from that release's exact schema; pin its source binding and complete locale artifacts in the application build.
- Distribute the expected manifest through the trusted application deployment.
- Admit before preparing; supply matching installed renderers/actions and the selected admitted locale.
- Keep application cleanup and async-operation policy separate from generic field constraints.
- Run `validate_forms_release_integration.py`, frontend tests, packed-package consumer tests and full browser acceptance.
- Record the exact changed-package version actually published before consumer adoption. A merged PR or local tarball is not published availability.

| Evidence | Coverage |
| --- | --- |
| ReleaseIntegration .NET probe and fixture drift test | Real publication/replay, 704 validation vectors, draft semantics, malformed conditions, compatibility |
| `release-integration.test.mjs` | .NET/AJV/standalone parity, complete release binding, immutable snapshots, foreign/retired/altered/mixed artifacts, unknown renderer/action rejection, unsafe UI/references, composed rules |
| Existing Localization contracts probe | Unchanged legacy compiler fixture and dependency boundaries |
| Browser suite | Published-to-rendered journey, conditional validity, ancestor/global/read-only behavior, Back/cleanup, cancellation/reset/changed-input races, four-language parity, RTL, accessibility and reflow |
| Clean NuGet and npm package consumers | Public package entry points without repository source imports; reproducible producer and runtime admission |

Run clean NuGet verification after packing:

```powershell
dotnet pack Orbyss.Forms.slnx -c Release --no-build -p:PackageOutputPath=C:/Code/Orbyss/forms/artifacts/nuget
python tests/validate_forms_release_packages.py --packages artifacts/nuget
python tests/validate_forms_frontend_packages.py
python tests/validate_forms_browser.py --install-browser
```

CI and Release include the new drift and packed-consumer gates. The full Chromium/Firefox/WebKit matrix remains mandatory for a release. On this Windows environment, the pinned Firefox binary currently fails to launch with `spawn UNKNOWN`, matching the existing documented limitation; no Firefox acceptance result may be inferred from Chromium/WebKit results.

## Local verification — 2026-09-12

- Locked .NET restore with an isolated package cache and Release build passed with zero build warnings or errors.
- Management, operations, localization/legacy serialization, in-memory storage, retirement, publication replay and fixture drift probes passed. Numeric-bound regressions also cover finite values outside the CLR decimal range.
- Locked npm install, workspace tests (including 704 cross-language condition vectors), reference TypeScript checking and clean npm consumer passed. The reference uses the existing React adapter's upstream declaration-check quarantine; application code remains strictly checked.
- All 15 NuGet package metadata checks and the clean public-API NuGet producer passed. CI/publication contract checks passed.
- Chromium desktop/phone portrait/phone landscape and WebKit desktop/tablet portrait/tablet landscape passed. Repeated WebKit journeys verified the rapid-edit state correction. Evidence is written to `artifacts/forms-browser/evidence/`.
- Physical-acceptance launcher, server isolation and CSP checks passed; this is not a manual physical-device acceptance result.

Firefox remains unverified locally because its pinned executable fails before page load. No release was tagged or published, and no consumer migration was performed.
