[CmdletBinding()]
param(
    [string]$Python = 'python'
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$suites = @(
    'validate_keycloak_advanced_browser.py',
    'validate_keycloak_password_recovery.py',
    'validate_keycloak_step_up.py',
    'validate_keycloak_key_rotation.py',
    'validate_keycloak_admin_api.py'
)

foreach ($suite in $suites) {
    Write-Host "Running advanced authentication suite: $suite"
    & $Python (Join-Path $projectRoot "tests\$suite")
    if ($LASTEXITCODE -ne 0) {
        throw "Advanced authentication suite failed: $suite"
    }
}

Write-Host 'Program Kit advanced authentication suites passed.'
