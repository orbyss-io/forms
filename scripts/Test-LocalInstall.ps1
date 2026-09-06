[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$sourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$testsRoot = [System.IO.Path]::GetFullPath((Join-Path $sourceRoot 'tests'))
$testRoot = [System.IO.Path]::GetFullPath((Join-Path $testsRoot '.lifecycle'))

if (-not $testRoot.StartsWith($testsRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Test target escaped the tests directory: $testRoot"
}
if (Test-Path -LiteralPath $testRoot) {
    throw "Refusing to overwrite an existing lifecycle test directory: $testRoot"
}

New-Item -ItemType Directory -Path $testRoot | Out-Null
try {
    Push-Location $testRoot
    specify init . --force --non-interactive --integration codex --script py --ignore-agent-tools `
        --extension (Join-Path $sourceRoot 'extensions\program-kit-governance')
    if ($LASTEXITCODE -ne 0) { throw 'Disposable Spec Kit initialization failed.' }

    specify extension add (Join-Path $sourceRoot 'extensions\program-kit-dotnet') --dev
    if ($LASTEXITCODE -ne 0) { throw 'Local .NET extension installation failed.' }

    specify preset add --dev (Join-Path $sourceRoot 'presets\program-kit-governance-preset')
    if ($LASTEXITCODE -ne 0) { throw 'Local governance preset installation failed.' }

    specify workflow add (Join-Path $sourceRoot 'workflows\program-kit-bootstrap') --dev
    if ($LASTEXITCODE -ne 0) { throw 'Local workflow installation failed.' }

    $extensionConfig = Get-Content -Raw -LiteralPath '.specify\extensions.yml'
    foreach ($expected in @('before_constitution', 'before_specify', 'after_specify', 'after_plan', 'after_tasks', 'before_implement', 'after_implement')) {
        if ($extensionConfig -notmatch [regex]::Escape($expected)) {
            throw "Expected hook '$expected' was not registered."
        }
    }

    $installedWorkflow = '.specify\workflows\program-kit-bootstrap\workflow.yml'
    if (-not (Test-Path -LiteralPath $installedWorkflow -PathType Leaf)) {
        throw 'Installed workflow definition was not found.'
    }
    $stepCount = @(Select-String -LiteralPath $installedWorkflow -Pattern '^  - id:').Count
    $sourceWorkflow = Join-Path $sourceRoot 'workflows\program-kit-bootstrap\workflow.yml'
    $expectedStepCount = @(Select-String -LiteralPath $sourceWorkflow -Pattern '^  - id:').Count
    if ($stepCount -ne $expectedStepCount) {
        throw "Installed workflow exposes $stepCount steps; expected $expectedStepCount from source."
    }

    $constitutionSkill = '.agents\skills\speckit-constitution\SKILL.md'
    $pythonResolver = '.specify\scripts\python\resolve_template.py'
    if (-not (Test-Path -LiteralPath $pythonResolver -PathType Leaf)) {
        throw 'Python-flavor Spec Kit resolver was not installed.'
    }
    if ((Get-Content -Raw -LiteralPath $constitutionSkill) -notmatch [regex]::Escape('.specify/scripts/python/resolve_template.py')) {
        throw 'The generated constitution skill does not reference the Python resolver.'
    }

    $validator = '.specify\extensions\program-kit-governance\scripts\governance_state.py'
    if (-not (Test-Path -LiteralPath $validator -PathType Leaf)) {
        throw 'Installed governance-state validator was not found.'
    }
    $codexPreflight = '.specify\extensions\program-kit-governance\scripts\codex_bootstrap_preflight.py'
    if (-not (Test-Path -LiteralPath $codexPreflight -PathType Leaf)) {
        throw 'Installed Codex bootstrap preflight was not found.'
    }
    $bootstrapSkill = '.agents\skills\speckit-program-kit-governance-bootstrap\SKILL.md'
    if (-not (Test-Path -LiteralPath $bootstrapSkill -PathType Leaf)) {
        throw 'Installed Codex-safe bootstrap skill was not found.'
    }
    $dotnetSync = '.specify\extensions\program-kit-dotnet\scripts\dotnet_sync.py'
    if (-not (Test-Path -LiteralPath $dotnetSync -PathType Leaf)) {
        throw 'Installed .NET sync extension was not found.'
    }
    $dotnetSkill = '.agents\skills\speckit-program-kit-dotnet-sync\SKILL.md'
    if (-not (Test-Path -LiteralPath $dotnetSkill -PathType Leaf)) {
        throw 'Installed .NET sync skill was not found.'
    }

    if ($env:CODEX_SESSION_ID -or $env:CODEX_THREAD_ID -or $env:CODEX_INTERNAL_ORIGINATOR_OVERRIDE) {
        $preflightOutput = (& specify workflow run program-kit-bootstrap `
            --input bootstrap_intake=docs/architecture/DOES-NOT-EXIST.json `
            --input integration=codex 2>&1 | Out-String)
        $preflightExitCode = $LASTEXITCODE
        $normalizedPreflightOutput = $preflightOutput -replace '\s+', ' '
        $paused = $preflightExitCode -eq 0 -and $normalizedPreflightOutput -match [regex]::Escape('Status: paused')
        $aborted = $preflightExitCode -ne 0 `
            -and $normalizedPreflightOutput -match [regex]::Escape('Status: aborted') `
            -and $normalizedPreflightOutput -match [regex]::Escape("Gate rejected by user at step 'confirm-agent-boundary-stop'")
        if (-not $paused -and -not $aborted) {
            throw "Codex agent preflight did not stop cleanly: $preflightOutput"
        }
        foreach ($expected in @('confirm-agent-boundary-stop')) {
            if ($normalizedPreflightOutput -notmatch [regex]::Escape($expected)) {
                throw "Workflow-visible Codex preflight stop is missing '$expected': $preflightOutput"
            }
        }
        if ($normalizedPreflightOutput -match '\[intake\]') {
            throw "Codex preflight dispatched intake before stopping: $preflightOutput"
        }
    }
} finally {
    if ((Get-Location).Path -eq $testRoot) {
        Pop-Location
    }
    $resolvedCleanup = [System.IO.Path]::GetFullPath($testRoot)
    if (-not $resolvedCleanup.StartsWith($testsRoot + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Cleanup target escaped the tests directory: $resolvedCleanup"
    }
    if (Test-Path -LiteralPath $resolvedCleanup) {
        Remove-Item -LiteralPath $resolvedCleanup -Recurse -Force
    }
}

Write-Host 'Local extension/workflow installation and hook checks passed.'
