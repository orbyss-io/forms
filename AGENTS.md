# Contributor instructions

- Forms owns its .NET, TypeScript, browser, packaging, and publication suites.
- Forms may depend on released Orbyss Foundation packages; it must not depend on Program Kit source.
- Keep form semantics provider-neutral and keep framework bindings thin.
- Run locked .NET restore/build, npm locked install/tests, clean package tests, and browser acceptance before tagging.
- A stable tag is only available after the complete Release workflow succeeds.
