[CmdletBinding()]
param(
    [string]$Subject = '',
    [switch]$LockedMode,
    [switch]$ForceEvaluate,
    [switch]$NoCache,
    [switch]$EnvironmentOnly
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$nugetConfig = Join-Path $root 'NuGet.config'
if (-not (Test-Path -LiteralPath $nugetConfig -PathType Leaf)) {
    throw "PKN101 managed restore requires the reviewed repository NuGet.config: $nugetConfig"
}
if ($EnvironmentOnly -and ($Subject -or $LockedMode -or $ForceEvaluate -or $NoCache)) {
    throw 'PKN101 -EnvironmentOnly cannot be combined with restore arguments.'
}

$cache = Join-Path $root '.program-kit/cache'
$env:NUGET_PACKAGES = Join-Path $cache 'nuget/packages'
$env:NUGET_HTTP_CACHE_PATH = Join-Path $cache 'nuget/http'
$env:NUGET_SCRATCH = Join-Path $cache 'nuget/scratch'
$env:NUGET_PLUGINS_CACHE_PATH = Join-Path $cache 'nuget/plugins'
$env:DOTNET_CLI_HOME = Join-Path $cache 'dotnet-home'
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:DOTNET_SKIP_FIRST_TIME_EXPERIENCE = '1'
$env:DOTNET_NOLOGO = '1'
if ($IsWindows -or $env:OS -eq 'Windows_NT') {
    $env:APPDATA = Join-Path $cache 'profile/roaming'
    $env:LOCALAPPDATA = Join-Path $cache 'profile/local'
}
$directories = @(
    $env:NUGET_PACKAGES,
    $env:NUGET_HTTP_CACHE_PATH,
    $env:NUGET_SCRATCH,
    $env:NUGET_PLUGINS_CACHE_PATH,
    $env:DOTNET_CLI_HOME
)
if ($IsWindows -or $env:OS -eq 'Windows_NT') {
    $directories += @($env:APPDATA, $env:LOCALAPPDATA)
}
try {
    New-Item -ItemType Directory -Force -Path $directories | Out-Null
}
catch {
    throw "PKN102 cannot prepare the repository-owned NuGet/.NET environment below $cache. $($_.Exception.Message)"
}
if ($EnvironmentOnly) { return }

if ($Subject) {
    $candidate = if ([System.IO.Path]::IsPathRooted($Subject)) {
        [System.IO.Path]::GetFullPath($Subject)
    }
    else {
        [System.IO.Path]::GetFullPath((Join-Path $root $Subject))
    }
    $relative = [System.IO.Path]::GetRelativePath($root, $candidate)
    if (
        [System.IO.Path]::IsPathRooted($relative) -or
        $relative -eq '..' -or
        $relative.StartsWith("..$([System.IO.Path]::DirectorySeparatorChar)") -or
        -not (Test-Path -LiteralPath $candidate -PathType Leaf) -or
        [System.IO.Path]::GetExtension($candidate) -notin '.sln', '.slnx', '.csproj', '.fsproj'
    ) {
        throw "PKN101 restore subject must be one solution or project file inside the repository: $Subject"
    }
    $restoreSubject = $candidate
}
else {
    $solutions = @(Get-ChildItem -LiteralPath $root -File | Where-Object { $_.Extension -in '.sln', '.slnx' })
    if ($solutions.Count -ne 1) {
        throw "PKN101 expected exactly one root solution in $root; found $($solutions.Count). Pass -Subject explicitly."
    }
    $restoreSubject = $solutions[0].FullName
}

$arguments = @('restore', $restoreSubject, '--configfile', $nugetConfig)
if ($LockedMode) { $arguments += '--locked-mode' }
if ($ForceEvaluate) { $arguments += '--force-evaluate' }
if ($NoCache) { $arguments += '--no-cache' }
& dotnet @arguments
if ($LASTEXITCODE -ne 0) {
    throw "PKN103 repository-isolated dotnet restore failed with exit code $LASTEXITCODE."
}
