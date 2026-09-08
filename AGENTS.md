# Contributor instructions

- Forms owns its .NET, TypeScript, browser, packaging, and publication suites.
- Forms may depend on released Orbyss Foundation packages and the released Localization abstractions package; it must not depend on Program Kit or Localization implementation source.
- Keep .NET projects directly under `src/`, TypeScript under `src/typescript`, and repository tooling under `scripts/`; do not introduce `src/dotnet` or a repository-level `eng` directory.
- Keep form semantics provider-neutral and keep framework bindings thin.
- Run locked .NET restore/build, npm locked install/tests, clean package tests, and browser acceptance before tagging.
- A stable tag is only available after the complete Release workflow succeeds.
