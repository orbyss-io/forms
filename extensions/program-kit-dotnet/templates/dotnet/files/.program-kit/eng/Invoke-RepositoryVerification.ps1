[CmdletBinding()]
param(
    [ValidateSet('CI', 'Release')]
    [string]$Mode = 'CI'
)

$ErrorActionPreference = 'Stop'
$repository = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$consumerPath = Join-Path $repository 'eng\verify.ps1'

& (Join-Path $PSScriptRoot 'Restore.ps1') -EnvironmentOnly
if (-not $?) {
    throw "Managed $Mode verification could not prepare the repository-owned NuGet/.NET environment."
}

if (Test-Path -LiteralPath $consumerPath) {
    $consumer = Get-Item -LiteralPath $consumerPath -Force
    if (-not $consumer.PSIsContainer -and ($consumer.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
        $resolved = (Resolve-Path -LiteralPath $consumer.FullName).Path
        $relative = [IO.Path]::GetRelativePath($repository, $resolved)
        if ([IO.Path]::IsPathRooted($relative) -or $relative -eq '..' -or $relative.StartsWith("..$([IO.Path]::DirectorySeparatorChar)")) {
            throw 'Consumer verification must resolve inside the repository.'
        }
        & $resolved
        if (-not $?) {
            throw 'Consumer verification failed.'
        }
        return
    }
    throw 'Consumer verification must be a regular repository file, not a directory or reparse point.'
}

& (Join-Path $PSScriptRoot 'Build.ps1') -SkipRunnableHost -LockedMode
if (-not $?) {
    throw "Managed $Mode verification fallback failed."
}
