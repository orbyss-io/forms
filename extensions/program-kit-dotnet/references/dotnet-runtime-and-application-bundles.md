# .NET runtime and runnable-host release profile

Apply this reference when .NET is selected unless intake explicitly opts out of the Program Kit runtime.

## Host boundary

- `ProgramKit.Host` is application-neutral plumbing: Nuplane package loading, the
  Nuplane-to-CShells assembly provider, CShells configuration/routing, CShells-only eager activation,
  and the versioned Program Kit secure-web profile selected from host configuration.
- It has no application-bundle parser, package/feature policy, database client, business endpoint,
  application permission identity, or feature-health aggregation.
- Actual business behavior arrives as runtime packages. Standard authenticated web plumbing is
  configured by the host's accepted Program Kit web profile; persistence, business endpoints,
  tasks, and health implementations remain explicit capabilities.
- Until a feature-health contribution interface exists, do not invent a host dependency-readiness model.

## Feature creation and activation closure

The authoritative activation shape is `CShells:Shells:<shell-name>:Features:<feature-identity>` in the real
consumer-owned `shells.json`. Add a reviewed selection deterministically with:

```text
python .program-kit/eng/feature_metadata.py activate --shells shells.json --shell <name> --feature <identity>
```

An activatable implementation/provider/bridge/composition project is packable, belongs to the solution, sets `ProgramKitFeatureIdentity`, declares an exact matching `[ShellFeature("<ProgramKitFeatureIdentity>")]`, and sets
`AssemblyName` equal to `PackageId`. It references host-supplied CShells/framework abstractions with
`PrivateAssets=all`; it does not reference the host, Nuplane runtime, or peer runtime implementations.
Optional dependency, route, and dormant metadata is embedded during pack.

Tasks cover the project, solution inclusion, explicit identity, `shells.json` activation, runnable-image
inclusion, and missing/duplicate/dependency/route/dormancy tests. `.program-kit/eng/runnable_host.py stage`
enforces those constraints while assembling image inputs. The host does not know or repeat this policy.

## Runnable-host release

One application release produces one runnable image. Its Dockerfile derives from the approved digest-pinned
`ProgramKit.Host`, copies the validated package closure to `/app/packages`, and adds the consumer-owned
`hostsettings.json` plus `shells.json`. Secrets stay in deployment configuration.

After the registry supplies the immutable image digest, the release workflow emits `runnable-host.json`.
The descriptor contains the application ID/version/source commit, image repository/tag/digest/reference,
and the exact secret-free settings plus their hashes. This descriptor is deployment/release evidence; it is
not a manifest interpreted by `ProgramKit.Host`.

Production package feeds, watching, reconciliation, and reload policy are application deployment choices.
Container health is also selected by the application once its feature-health contract is known.

## Boundaries retained from the wider .NET profile

- Central package management, locked restore, deterministic pack, and package-source mapping are mandatory.
- `shells.json` and `hostsettings.json` remain scaffold-once consumer-owned inputs.
- Managed OpenAPI production runs after package-closure staging through
  `.program-kit/eng/openapi_pipeline.py`. Consumers register complete producer, compatibility,
  isolated client-generation, and application-compile contracts in
  `.program-kit/openapi-contracts.json`; the external host remains application-neutral.
- Core and persistence guidance remains context-owned. No provider-private model, shared `DbContext`,
  generic repository/store/unit-of-work contract, provider, or readiness probe belongs in the host.
