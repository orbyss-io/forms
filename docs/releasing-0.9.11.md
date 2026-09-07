# Releasing Program Kit 0.9.11

This patch removes the circular C4 review gate while preserving explicit bootstrap confirmation.
Program Kit components advance to `0.9.11`; runtime packages and the host image remain
`0.9.9-preview.1`.

Before tagging, run the deterministic release gates:

```powershell
./scripts/Test-ProgramKit.ps1 -BrowserEngines 'chromium,webkit'
./scripts/Test-LocalInstall.ps1
dotnet restore ProgramKit.slnx --force-evaluate --configfile NuGet.config
dotnet restore ProgramKit.slnx --locked-mode --configfile NuGet.config
dotnet build ProgramKit.slnx -c Release --no-restore
dotnet pack ProgramKit.slnx -c Release --no-build -p:PackageOutputPath="$PWD/artifacts/nuget"
python tests/validate_release_install.py
```

The C4 regression must distinguish exact hash-bound draft review from confirmed baseline review,
reject stale or malformed draft artifacts, prove repository immutability, and keep the outer
bootstrap validator confirmation-gated. The packaged clean-consumer test must perform draft artifact
generation, draft C4 inspection, explicit confirmation, and final validation in that order.

Create and push the stable tag only from the fully validated and explicitly approved release commit:

```powershell
git tag v0.9.11
git push origin main v0.9.11
```

The complete ordered Release workflow must succeed before consumers are told to upgrade. If the
candidate fails, preserve the failure evidence, repair and validate the commit, obtain approval for
that exact corrected commit, and recreate the same `v0.9.11` tag according to repository policy.
