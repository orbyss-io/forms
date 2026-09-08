# Frontend package publication decision

Decision date: 2026-09-06

Orbyss Forms frontend packages will publish from the tagged GitHub Actions release workflow to
GitHub Packages at `npm.pkg.github.com` under the `@orbyss-io` scope. Consumers will install only the
adapters they select. No manual package upload is part of the release procedure.

The publication workflow is enabled for the approved twelve-package engine family. It:

- derives every package version from `RUNTIME_VERSION` (`0.1.0`) while requiring the
  release tag to match `VERSION` (`v0.9.9`);
- authenticate with the workflow's narrowly scoped GitHub package permission, never a committed
  token;
- run the clean locked install, build, tests, browser acceptance and package dry runs before publish;
- publishes immutable packages from the tagged commit, attests the packed tarballs through GitHub
  artifact attestations, and fails rather than republish an existing version;
- verifies every published package by installing the whole exact-version family into a clean
  consumer from GitHub Packages; and
- treat a failed release pipeline as an unreleased version so a corrected commit replaces the failed
  tag, following the repository's existing release policy.

CI and publication use different change-selection rules. Branch and pull-request frontend CI is a
separate workflow with native path filters. GitHub does not evaluate path filters for tag pushes, so
publication must instead compare the tagged commit with the last successfully published commit for
each independently released family. A deterministic release plan records the selected families and
their artifact hashes before any write permission is granted.

The publication units are the complete synchronized dependency families: frontend npm packages
and Orbyss Forms/Localization NuGet packages. Because frontend packages use exact internal versions
and .NET projects share `FormsVersion`, a change to one member can require its family-wide dependent
closure. The initial stable-release policy therefore validates and publishes both exact package
families together. Per-package publishing is deferred until independent versions and a tested
dependency-closure planner exist.

The packages use the `latest` dist-tag because they are independently versioned stable Forms
artifacts. An optional future npmjs.com mirror requires a separate explicit decision. It is
not part of the default publication topology.

The repository-wide family selection and least-authority rules are defined in
`docs/release-family-publication.md`.
