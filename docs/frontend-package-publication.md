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

An optional future npmjs.com mirror requires a separate explicit decision. It is not part of the
default publication topology.
