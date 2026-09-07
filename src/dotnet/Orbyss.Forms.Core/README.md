# Orbyss.Forms.Core

Provider-neutral form validation and compatibility analysis. This package understands Program
Kit's semantic form model, but has no dependency on JSON Forms, ASP.NET Core, persistence, a DI
container, or a UI editor.

Use `FormDefinitionValidator` before compilation or mutation. Use
`DefaultFormCompatibilityAnalyzer` before publishing a candidate over an existing release.
