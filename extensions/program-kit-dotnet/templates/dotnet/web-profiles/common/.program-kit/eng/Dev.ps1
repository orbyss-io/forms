[CmdletBinding()]
param(
    [switch]$IdentityOnly,
    [switch]$SkipBuild,
    [string]$ComposeOverlay = ''
)

$ErrorActionPreference = 'Stop'
$repository = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$compose = Join-Path $repository 'deploy\compose.identity.yml'
$applicationCompose = Join-Path $repository 'deploy\compose.application.yml'
$topologyValidator = Join-Path $PSScriptRoot 'compose_topology.py'

python (Join-Path $PSScriptRoot 'preflight.py')
if ($LASTEXITCODE -ne 0) { throw 'Program Kit pre-host prerequisites failed.' }
$profileRecord = Join-Path $repository '.program-kit\web-profile.json'
if (-not (Test-Path -LiteralPath $profileRecord -PathType Leaf)) {
    throw 'The synchronized web-profile record is missing.'
}
$selectedWebProfile = (Get-Content -LiteralPath $profileRecord -Raw | ConvertFrom-Json).profile
if ($selectedWebProfile -eq 'spa-pkce-v1') {
    $spaVerifier = Join-Path $PSScriptRoot 'verify_spa_profile.py'
    if (-not (Test-Path -LiteralPath $spaVerifier -PathType Leaf)) {
        throw 'The selected SPA-PKCE profile verifier is missing.'
    }
    python $spaVerifier --repository $repository
    if ($LASTEXITCODE -ne 0) { throw 'The synchronized SPA-PKCE profile is invalid.' }
}
elseif ($selectedWebProfile -ne 'bff-cookie-v1') {
    throw "The synchronized web profile '$selectedWebProfile' is unsupported by Dev.ps1."
}

$applicationComposeArguments = @('compose', '-f', $applicationCompose)
$overlay = $null
if (-not [string]::IsNullOrWhiteSpace($ComposeOverlay)) {
    $overlay = [System.IO.Path]::GetFullPath((Join-Path $repository $ComposeOverlay))
    $relativeOverlay = [System.IO.Path]::GetRelativePath($repository, $overlay)
    if ($relativeOverlay.StartsWith('..') -or -not (Test-Path -LiteralPath $overlay -PathType Leaf)) {
        throw 'ComposeOverlay must name a consumer-owned file inside the repository.'
    }
    $applicationComposeArguments += @('-f', $overlay)
}

$topologyArguments = @('--repository', $repository, '--identity-compose', $compose)
if (-not $IdentityOnly) {
    $topologyArguments += @('--application-compose', $applicationCompose)
    if ($null -ne $overlay) { $topologyArguments += @('--overlay', $overlay) }
}
python $topologyValidator @topologyArguments
if ($LASTEXITCODE -ne 0) { throw 'The merged local Compose topology is disconnected; no service was started.' }

docker compose -f $compose up -d --wait
if ($LASTEXITCODE -ne 0) { throw 'The pinned local Keycloak service did not become ready.' }

if ($IdentityOnly) {
    python $topologyValidator @topologyArguments --verify-running
    if ($LASTEXITCODE -ne 0) { throw 'The running identity topology differs from the desired Compose model.' }
    Write-Host 'Local identity is ready at http://localhost:8080 (realm program-kit).'
    exit 0
}

if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot 'Build.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'The application build failed.' }
}

if ([string]::IsNullOrWhiteSpace($env:PROGRAMKIT_HOST_IMAGE)) {
    throw 'Set PROGRAMKIT_HOST_IMAGE to the approved digest-pinned ProgramKit.Host image, then rerun Dev.ps1. Identity remains ready.'
}

$applicationImage = 'program-kit-consumer:local'
docker build --build-arg "PROGRAMKIT_HOST_IMAGE=$($env:PROGRAMKIT_HOST_IMAGE)" -t $applicationImage $repository
if ($LASTEXITCODE -ne 0) { throw 'The local application image build failed.' }

$applicationComposeArguments += @('up', '-d', '--force-recreate', '--remove-orphans')
docker @applicationComposeArguments
if ($LASTEXITCODE -ne 0) { throw 'The local runnable host did not start.' }

python $topologyValidator @topologyArguments --verify-running
if ($LASTEXITCODE -ne 0) { throw 'The running local topology differs from the merged desired Compose model.' }
