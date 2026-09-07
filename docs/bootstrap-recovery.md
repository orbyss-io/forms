# Recovering a hash-approved bootstrap after roadmap drift

Program Kit 0.6.10 supports recovery without cleaning or reinitializing the consumer repository.
The failed run itself must not be resumed: Spec Kit persists the workflow definition with each run,
so resuming a 0.6.8 run would retry its old final step without the new synchronization and
cross-artifact validation steps.

Do not edit `architecture.md`, `traceability.md`, the bootstrap review packet, or approval JSON by
hand. Those artifacts are hash-bound. Recovery uses a new 0.6.10 workflow run over the existing
repository. It regenerates architecture and roadmap artifacts, synchronizes the derived roadmap
views, validates them before review, regenerates the final review packet, requires fresh human
approval, replaces `bootstrap-approval.json` with hashes for the newly approved content, reruns
readiness, and only then completes bootstrap.

The current workflow has no adapter from a legacy design input. If the repository does not already
contain a validated `docs/architecture/bootstrap-intake.json`, open the installed integration and
invoke the Program Kit bootstrap skill with the existing project intent and artifacts. Complete its
adaptive questions, review the C4/domain map, and confirm the new intake before continuing. Do not
infer or manufacture a confirmed intake from the failed run.

From a normal user-owned PowerShell prompt in the affected repository, run:

```powershell
Set-Location C:\path\to\PriceCalculator

$bootstrapIntake = 'docs/architecture/bootstrap-intake.json'
$integrationState = Get-Content -Raw -LiteralPath '.specify\integration.json' | ConvertFrom-Json
$integration = [string]$integrationState.default_integration
if ([string]::IsNullOrWhiteSpace($integration)) {
    $integration = [string]$integrationState.integration
}

# Download, verify, and extract the target full Program Kit release first. The
# release-owned updater avoids catalog transport and does not trust a bundle
# record until every installed primitive and managed baseline converges.
$releaseRoot = 'C:\path\to\program-kit-0.9.11'
python "$releaseRoot\scripts\upgrade_program_kit.py" `
  --release-root $releaseRoot `
  --target . `
  --integration $integration
if ($LASTEXITCODE -ne 0) { throw 'Sequential Program Kit upgrade failed.' }

python .specify/extensions/program-kit-governance/scripts/governance_state.py validate-installation
if ($LASTEXITCODE -ne 0) { throw 'Program Kit installation is not version-coherent.' }

specify workflow run program-kit-bootstrap `
  --input "bootstrap_intake=$bootstrapIntake" `
  --input "integration=$integration"
if ($LASTEXITCODE -ne 0) { throw 'Recovered bootstrap did not complete.' }

python .specify/extensions/program-kit-governance/scripts/governance_state.py validate-completion
if ($LASTEXITCODE -ne 0) { throw 'Bootstrap completion hashes are invalid.' }
```

Review and decide every displayed gate in the new run. In particular, the final bootstrap gate must
show the regenerated packet before approval. Do not run `specify workflow resume bf551b86`; retain
that failed run as historical evidence.

## Recovering an abandoned run still marked running

Program Kit 0.6.11 adds explicit recovery for this condition.

Spec Kit records a normal interruption as a terminal workflow state, but a hard process termination
can leave its last persisted state as `running`. Program Kit blocks a replacement bootstrap before
intake when it finds such a record because concurrent bootstrap runs would mutate the same governed
artifacts.

First verify that the listed run has no live `specify workflow` process. Then use the exact command
printed by the preflight diagnostic, from the same normal user-owned shell:

```powershell
python .specify/extensions/program-kit-governance/scripts/codex_bootstrap_preflight.py `
  --abandon-run <run-id>
```

The command accepts only a validated `program-kit-bootstrap` run whose current status is `running`.
It atomically changes that run to `aborted`, records the explicit operator action in `log.jsonl`, and
leaves the workflow snapshot, inputs, step results, and prior log evidence intact. It refuses other
workflow types and already-terminal runs. Start a new bootstrap afterward; do not edit or delete the
run directory by hand.
