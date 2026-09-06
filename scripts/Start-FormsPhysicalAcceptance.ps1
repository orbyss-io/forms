[CmdletBinding()]
param(
    [ValidateRange(0, 65535)]
    [int]$Port = 4173,
    [switch]$Install
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $python) {
    $python = Get-Command py -ErrorAction Stop
    $arguments = @('-3')
} else {
    $arguments = @()
}

$arguments += @(
    (Join-Path $projectRoot 'tests\serve_forms_physical_acceptance.py'),
    '--host',
    '0.0.0.0',
    '--port',
    $Port
)
if ($Install) {
    $arguments += '--install'
}

Write-Host 'Building and serving the Program Kit Forms physical-acceptance showcase.'
Write-Host 'Use only on a trusted private network. Press Ctrl+C when testing is complete.'
& $python.Source @arguments
if ($LASTEXITCODE -ne 0) {
    throw 'The Forms physical-acceptance showcase failed.'
}
