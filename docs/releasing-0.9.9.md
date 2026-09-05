# Releasing Program Kit 0.9.9

This release adds provider-neutral authentication and identity-administration packages, the Keycloak
adapter and advanced conformance suites. Components are `0.9.9`; runtime packages and the host image
are `0.9.9-preview.1`.

Before tagging, run:

```powershell
./scripts/Test-ProgramKit.ps1
./scripts/Test-AdvancedAuthentication.ps1
./scripts/Test-LocalInstall.ps1
dotnet restore ProgramKit.slnx --force-evaluate --configfile NuGet.config
dotnet restore ProgramKit.slnx --locked-mode --configfile NuGet.config
dotnet build ProgramKit.slnx -c Release --no-restore
dotnet pack ProgramKit.slnx -c Release --no-build -p:PackageOutputPath="$PWD/artifacts/nuget"
python tests/validate_release_install.py
```

The advanced suite is local/manual and must not be added to unattended CI. Its evidence is required for
this authentication release because the provider adapter, themes, and authenticator contracts changed.

Create and push the stable tag only from the fully validated and explicitly approved release commit:

```powershell
git tag v0.9.9
git push origin main v0.9.9
```

If the release pipeline fails before a stable release exists, repair the candidate and replace the
failed `v0.9.9` tag with the fixed, explicitly approved commit. Do not create a drift version and do not
announce or install 0.9.9 until the complete ordered publication workflow succeeds.
