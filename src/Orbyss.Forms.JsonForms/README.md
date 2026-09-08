# Orbyss.Forms.JsonForms

Compiles Orbyss Forms's provider-neutral form model into bundled JSON Schema 2020-12 and JSON Forms
UI Schema artifacts. Compilation also emits stable renderer, translation, and action manifests and
SHA-256 evidence. It does not execute JavaScript, fetch remote references, or depend on a UI editor.

The emitted `Orbyss.Forms.Wizard` and `Orbyss.Forms.ActionBar` requirements are resolved by separately
installed frontend renderer packages.
