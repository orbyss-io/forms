[CmdletBinding()]
param(
    [ValidateSet('codex', 'claude')]
    [string]$Integration = 'codex',

    [ValidateSet('clean-bootstrap')]
    [string]$Scenario = 'clean-bootstrap',

    [ValidateRange(60, 86400)]
    [int]$TimeoutSeconds = 7200,

    [switch]$ExerciseIntakeSkill,

    [ValidateRange(60, 86400)]
    [int]$IntakeTimeoutSeconds = 3600,

    [switch]$ContinueFirstSlice,

    [ValidateRange(60, 86400)]
    [int]$FirstSliceTimeoutSeconds = 7200,

    [switch]$Approved
)

$ErrorActionPreference = 'Stop'

if (-not $Approved) {
    throw @'
LIVE_ACCEPTANCE_APPROVAL_REQUIRED

This suite starts paid coding-agent sessions and can run for a long time.
Run it only when the user explicitly requests a live bootstrap acceptance run.
Pass -Approved to acknowledge that request; publication must not prompt for this suite automatically.
'@
}

if ($env:CI -or $env:GITHUB_ACTIONS -or $env:TF_BUILD -or $env:BUILD_BUILDID) {
    throw 'LIVE_ACCEPTANCE_CI_FORBIDDEN: The paid live bootstrap suite must not run in CI.'
}

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$uv = Get-Command uv -ErrorAction Stop
$toolRoot = (& $uv.Source tool dir).Trim()

if ($IsWindows -or $env:OS -eq 'Windows_NT') {
    $python = Join-Path $toolRoot 'specify-cli\Scripts\python.exe'
} else {
    $python = Join-Path $toolRoot 'specify-cli/bin/python'
}

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Could not locate the specify-cli Python environment at $python"
}

$runner = Join-Path $projectRoot 'tests\live\run_bootstrap_acceptance.py'
$arguments = @(
    $runner
    '--scenario'
    $Scenario
    '--integration'
    $Integration
    '--timeout-seconds'
    $TimeoutSeconds
    '--approved'
)
if ($ContinueFirstSlice) {
    $arguments += @('--continue-first-slice', '--first-slice-timeout-seconds', $FirstSliceTimeoutSeconds)
}
if ($ExerciseIntakeSkill) {
    if ($Integration -ne 'codex') {
        throw 'INTAKE_SKILL_CODEX_REQUIRED: -ExerciseIntakeSkill currently requires -Integration codex.'
    }
    $arguments += @('--exercise-intake-skill', '--intake-timeout-seconds', $IntakeTimeoutSeconds)
}

& $python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Live acceptance failed with exit code $LASTEXITCODE. Inspect artifacts/live-acceptance."
}

if ($ExerciseIntakeSkill -and $ContinueFirstSlice) {
    Write-Host 'Live conversational intake, bootstrap, and first-slice acceptance passed.'
} elseif ($ExerciseIntakeSkill) {
    Write-Host 'Live conversational intake and bootstrap acceptance passed.'
} elseif ($ContinueFirstSlice) {
    Write-Host 'Live bootstrap and first-slice acceptance passed.'
} else {
    Write-Host 'Live bootstrap acceptance passed.'
}
