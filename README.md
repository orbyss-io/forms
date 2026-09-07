# Orbyss Forms

A cohesive Forms product maintained by Orbyss. This repository owns the .NET form and localization
capabilities together with the TypeScript JSON Forms runtime, framework bindings, and UI contracts.

Forms depends on released `Orbyss.Foundation.*` building blocks. It does not depend on the Program
Kit AI extension. Program Kit separately carries the knowledge required to select and compose Forms.

## Published families

- `Orbyss.Forms.*` and `Orbyss.Localization.*` NuGet packages.
- `@orbyss-io/forms-*` packages in GitHub Packages.

The first independently versioned release is `0.1.0`. All packages in each language family share the
repository version so their internal contracts remain coherent.

## Local validation

Foundation `0.1.0` must be available from NuGet.org or a local package source.

```powershell
dotnet restore Orbyss.Forms.slnx --locked-mode --configfile NuGet.config
dotnet build Orbyss.Forms.slnx -c Release --no-restore
python tests/validate_forms_management.py
python tests/validate_forms_operations.py
python tests/validate_forms_localization_contracts.py
python tests/validate_inmemory_storage.py
python tests/validate_forms_frontend.py --install
python tests/validate_forms_frontend_packages.py
```

Stable tags must exactly match `VERSION`. The release workflow publishes both the NuGet and npm
families only after their complete deterministic suites pass.
