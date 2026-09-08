# Changelog

## 0.1.1

- Preserve dependency-free `Orbyss.Forms.Abstractions` while replacing the ambiguous `Core` and `Application` packages with cohesive `JsonForms` and `Management` implementations.
- Rename the operational MCP packages to `Orbyss.Forms.Submissions.Tool` and `Orbyss.Forms.Submissions.Mcp.AspNetCore`.
- Add opt-in CShells composition features to JSON Forms, management, localization, submissions, filesystem storage, and in-memory storage implementations.
- Add a separately authorized local NuGet CLI command for retiring the four superseded 0.1.0 package identities after the complete 0.1.1 family is public.

## 0.1.0

- Extract Forms from Program Kit into an independently versioned product.
- Keep `Orbyss.Forms.Localization` as an explicit bridge to the independently released, dependency-free `Orbyss.Localization.Abstractions` contract package.
- Rename frontend packages to `@orbyss-io/forms-*`.
- Depend on released Orbyss Foundation building blocks instead of repository-owned runtime source.
