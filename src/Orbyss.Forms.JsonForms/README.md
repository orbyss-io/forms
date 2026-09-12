# Orbyss.Forms.JsonForms

Compiles Orbyss Forms's provider-neutral form model into bundled JSON Schema 2020-12 and JSON Forms
UI Schema artifacts. Compilation also emits stable renderer, translation, and action manifests and
SHA-256 evidence. It does not execute JavaScript, fetch remote references, or depend on a UI editor.

Select `OrbyssFormsJsonFormsFeature` to register the default `FormDefinitionValidator` and
`JsonFormsCompiler`. Registrations are replaceable, so a modular host may supply either contract
before activating the feature.

The emitted `Orbyss.Forms.Wizard` and `Orbyss.Forms.ActionBar` requirements are resolved by separately
installed frontend renderer packages.

Typed required conditions compile to JSON Schema `if`/`then`. Combined presentation conditions
preserve ancestor enablement and read-only precedence; leaf visibility may introduce a standard
`VerticalLayout`. Consumer renderers must honor visibility and propagate enabled state. See
`docs/immutable-release-integration.md` in the repository for the public producer and adoption recipe.
