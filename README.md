# Orbyss Forms

A cohesive Forms product maintained by Orbyss. This repository owns the .NET form capabilities
together with the TypeScript JSON Forms runtime, framework bindings, and UI contracts.

Forms depends only on released `Orbyss.Foundation.*` building blocks and, for the optional
`Orbyss.Forms.Localization` bridge, released `Orbyss.Localization.Abstractions`. It does not depend
on the Program Kit AI extension. Program Kit separately carries the knowledge required to select
and compose Forms.

## Published families

- 16 `Orbyss.Forms.*` NuGet packages, including the optional Localization integration bridge.
- 12 `@orbyss-io/forms-*` packages in GitHub Packages.

The first independently versioned release is `0.1.0`. All packages in each language family share the
repository version so their internal contracts remain coherent.

## Local validation

Foundation `0.1.0` and Localization Abstractions `0.1.0` must be publicly available from NuGet.org.

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
