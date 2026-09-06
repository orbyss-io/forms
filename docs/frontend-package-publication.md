# Frontend package publication decision

Decision date: 2026-09-06

Program Kit frontend packages will publish from the tagged GitHub Actions release workflow to
GitHub Packages at `npm.pkg.github.com` under the `@orbyss` scope. Consumers will install only the
adapters they select. No manual package upload is part of the release procedure.

The publication workflow remains intentionally disabled until the approved frontend package set is
complete. When it is enabled, it must:

- derive every package version from the repository `VERSION` and require an exactly matching tag;
- authenticate with the workflow's narrowly scoped GitHub package permission, never a committed
  token;
- run the clean locked install, build, tests, browser acceptance and package dry runs before publish;
- publish immutable packages from the tagged commit, attach provenance where GitHub's npm registry
  supports it, and fail rather than republish an existing version;
- verify every published package by installing it into a clean consumer from GitHub Packages; and
- treat a failed release pipeline as an unreleased version so a corrected commit replaces the failed
  tag, following the repository's existing release policy.

CI and publication use different change-selection rules. Branch and pull-request frontend CI is a
separate workflow with native path filters. GitHub does not evaluate path filters for tag pushes, so
publication must instead compare the tagged commit with the last successfully published commit for
each independently released family. A deterministic release plan records the selected families and
their artifact hashes before any write permission is granted.

The publication units are the complete synchronized dependency families: frontend npm packages,
Program Kit NuGet packages, the host container image, and bootstrap/release assets. Because frontend
packages use exact internal versions and .NET projects share `ProgramKitVersion`, a change to one
member can require its family-wide dependent closure. The safe initial policy is therefore to
publish all packages in a changed family, skip every unchanged family, and publish nothing for a
docs-only release. Per-package publishing is deferred until independent versions and a tested
dependency-closure planner exist.

An optional future npmjs.com mirror requires a separate explicit decision. It is not part of the
default publication topology.

The repository-wide family selection and least-authority rules are defined in
`docs/release-family-publication.md`.
