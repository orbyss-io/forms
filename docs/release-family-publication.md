# Release-family publication policy

Program Kit is a monorepo, but its deployable outputs are separate release families. Validation and
publication must not grant one family authority over another.

## Family boundaries

| Family | Primary inputs | Initial publication unit |
| --- | --- | --- |
| Frontend npm | `src/typescript`, its browser fixtures and shared JS toolchain | all 12 exact-versioned `@orbyss` engine packages |
| Program Kit NuGet | `src/dotnet`, solution/build/package lock inputs | all packable projects sharing `ProgramKitVersion` |
| Host container | Host Dockerfile plus the transitive .NET host graph and runtime version | one immutable multi-platform image |
| Bootstrap assets | extensions, presets, workflows, catalogs and bundle build scripts | one versioned release-asset set |

A cross-cutting input can select more than one family. Documentation-only changes select none.
Individual packages are not publication units while their internal dependencies use exact shared
versions. Selective per-package publishing requires independent versions and a tested transitive
dependency-closure planner first.

## CI selection

Branch and pull-request workflows may use native GitHub path filters as a cost optimization. Each
family keeps a manually dispatchable validation path, read-only repository permission and its own
named checks. A skipped family is not evidence that it passed; branch-protection rules must account
for path-filtered checks.

## Release selection

GitHub does not evaluate path filters for tag pushes. A tag release must therefore start with a
read-only classifier that compares the tagged commit with each family's last successfully published
commit. The classifier creates a deterministic release plan containing:

- selected families and baseline commits;
- family versions and exact source commit;
- packed artifact identities and hashes; and
- the validation evidence required before each selected publication.

Only a selected family's reusable publishing workflow receives its narrowly scoped write permission
and protected environment. Unselected jobs do not receive credentials and do not build or publish.
If classification encounters an unknown or cross-cutting path, it fails closed or selects every
possibly affected family.

For a failed publication, the version remains unreleased. Repair the commit and replace the failed
tag according to the repository release policy; do not create version drift merely to retry.

The first publication of a Program Kit-owned renderer or other visual component additionally
requires approved manual physical-device and assistive-technology evidence. Engine-only bindings
that publish no markup or CSS use the automated consumer-renderer browser matrix; the consuming
application owns physical acceptance for its selected renderer and design system.
