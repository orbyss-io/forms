[CmdletBinding()]
param(
    [switch]$SkipTests,
    [Alias('SkipBundle')]
    [switch]$SkipRunnableHost,
    [switch]$LockedMode,
    [switch]$InitializeOpenApiBaseline,
    [switch]$UpdateOpenApiArtifact
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$version = (Get-Content -Raw -LiteralPath (Join-Path $root 'VERSION')).Trim()
if ($version -notmatch '^\d+\.\d+\.\d+([-.][0-9A-Za-z.-]+)?$') {
    throw "VERSION is not a valid SemVer value: '$version'"
}

$solutions = @(Get-ChildItem -LiteralPath $root -File | Where-Object { $_.Extension -in '.sln', '.slnx' })
if ($solutions.Count -ne 1) {
    throw "Expected exactly one solution in $root; found $($solutions.Count)."
}

function Get-TestProjectCount {
    param(
        [Parameter(Mandatory)]
        [string]$SolutionPath
    )

    $solutionDirectory = Split-Path -Parent $SolutionPath
    $solutionProjectsOutput = @(& dotnet sln $SolutionPath list 2>&1)
    if ($LASTEXITCODE -ne 0) {
        $solutionProjectsOutput | ForEach-Object { Write-Host $_ }
        throw "Could not enumerate projects in solution $SolutionPath."
    }

    $projectPaths = @(
        $solutionProjectsOutput |
            ForEach-Object { ([string]$_).Trim() } |
            Where-Object { $_ -match '(?i)\.(csproj|fsproj|vbproj)$' } |
            ForEach-Object {
                if ([System.IO.Path]::IsPathRooted($_)) {
                    [System.IO.Path]::GetFullPath($_)
                }
                else {
                    [System.IO.Path]::GetFullPath((Join-Path $solutionDirectory $_))
                }
            }
    )

    $testProjectCount = 0
    foreach ($projectPath in $projectPaths) {
        if (-not (Test-Path -LiteralPath $projectPath -PathType Leaf)) {
            throw "Solution project does not exist: $projectPath"
        }

        $testPropertyOutput = @(& dotnet msbuild $projectPath -nologo -verbosity:quiet -getProperty:IsTestProject 2>&1)
        if ($LASTEXITCODE -ne 0) {
            $testPropertyOutput | ForEach-Object { Write-Host $_ }
            throw "Could not evaluate IsTestProject for $projectPath."
        }

        $testProperty = ($testPropertyOutput -join "`n").Trim()
        if ([string]::IsNullOrWhiteSpace($testProperty)) {
            continue
        }

        $isTestProject = $false
        if (-not [bool]::TryParse($testProperty, [ref]$isTestProject)) {
            throw "IsTestProject for $projectPath is not a Boolean value: '$testProperty'"
        }
        if ($isTestProject) {
            $testProjectCount++
        }
    }

    return $testProjectCount
}

$artifacts = Join-Path $root 'artifacts'
$packages = Join-Path (Join-Path $artifacts 'packages') $version
$openApiRegistry = Join-Path $root '.program-kit/openapi-contracts.json'
$openApiEnabled = $false
if (Test-Path -LiteralPath $openApiRegistry) {
    $openApiConfiguration = Get-Content -Raw -LiteralPath $openApiRegistry | ConvertFrom-Json
    if ($openApiConfiguration.schemaVersion -ne 1 -or $null -eq $openApiConfiguration.contracts) {
        throw 'OpenAPI registry must use schemaVersion 1 and declare a contracts array.'
    }
    $openApiEnabled = @($openApiConfiguration.contracts).Count -gt 0
}
New-Item -ItemType Directory -Force -Path $packages | Out-Null

if ($LockedMode) {
    & (Join-Path $PSScriptRoot 'Restore.ps1') -Subject $solutions[0].FullName -LockedMode
}
else {
    & (Join-Path $PSScriptRoot 'Restore.ps1') -Subject $solutions[0].FullName
}
if (-not $?) { throw 'Managed repository-isolated restore failed.' }
dotnet build $solutions[0].FullName -c Release --no-restore -p:Version=$version
if ($LASTEXITCODE -ne 0) { throw 'dotnet build failed.' }

if (-not $SkipTests) {
    $testProjectCount = Get-TestProjectCount -SolutionPath $solutions[0].FullName
    if ($testProjectCount -gt 0) {
        dotnet test --solution $solutions[0].FullName -c Release --no-build -p:Version=$version
        if ($LASTEXITCODE -ne 0) { throw 'dotnet test failed.' }
    }
    else {
        Write-Host 'No .NET test projects are included in the solution; skipping dotnet test.'
    }
}

dotnet pack $solutions[0].FullName -c Release --no-build -p:Version=$version -p:PackageOutputPath=$packages
if ($LASTEXITCODE -ne 0) { throw 'dotnet pack failed.' }

if (-not $SkipRunnableHost -or $openApiEnabled) {
    python (Join-Path $PSScriptRoot 'runnable_host.py') stage --repository $root --packages $packages `
        --output (Join-Path $artifacts 'runnable-host')
    if ($LASTEXITCODE -ne 0) { throw 'Runnable-host staging failed.' }
}

if ($openApiEnabled) {
    $openApiArguments = @('--repository', $root, '--registry', '.program-kit/openapi-contracts.json')
    if ($InitializeOpenApiBaseline) { $openApiArguments += '--initialize-baselines' }
    if ($UpdateOpenApiArtifact) { $openApiArguments += '--update-artifacts' }
    python (Join-Path $PSScriptRoot 'openapi_pipeline.py') @openApiArguments
    if ($LASTEXITCODE -ne 0) { throw 'Producer-first OpenAPI contract pipeline failed.' }
}
