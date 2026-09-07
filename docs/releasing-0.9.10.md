# Releasing Program Kit 0.9.10

This governance-usability release adds a safe, directly invokable C4 projection viewer and makes
architecture review actionable from bootstrap gates and review packets. Program Kit components
advance to `0.9.10`; runtime packages and the host image remain `0.9.9-preview.1` because no runtime
source or package contract changed.

Before tagging, run the deterministic release gates:

```powershell
./scripts/Test-ProgramKit.ps1
./scripts/Test-LocalInstall.ps1
dotnet restore ProgramKit.slnx --force-evaluate --configfile NuGet.config
dotnet restore ProgramKit.slnx --locked-mode --configfile NuGet.config
dotnet build ProgramKit.slnx -c Release --no-restore
dotnet pack ProgramKit.slnx -c Release --no-build -p:PackageOutputPath="$PWD/artifacts/nuget"
python tests/validate_release_install.py
```

The C4 regression must cover freshness and intake binding, invalid and missing projections, local
Docker/image and Java/WAR discovery, Windows and POSIX path construction, port conflicts, repeated
invocation, repository immutability, and cleanup. The realistic installed-consumer test must inspect
the generated projection without contacting an external service. Physical acceptance may use the
exact pinned local Structurizr image only with explicit user authorization.

Create and push the stable tag only from the fully validated and explicitly approved release commit:

```powershell
git tag v0.9.10
git push origin main v0.9.10
```

The complete ordered Release workflow must succeed before consumers are told to upgrade. If the
candidate fails, preserve the failure evidence, repair and validate the commit, obtain approval for
that exact corrected commit, and recreate the same `v0.9.10` tag according to repository policy.
