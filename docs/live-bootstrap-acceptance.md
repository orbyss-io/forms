# Live bootstrap acceptance suite

The live bootstrap acceptance suite proves that a packaged Program Kit candidate can complete the
real agentic workflow from initialization through final readiness. It is intentionally separate
from deterministic source, packaging, and simulated lifecycle tests.

## Cost and request boundary

The suite launches paid coding-agent sessions, may run for more than an hour, and is never executed
by CI. It is entirely user-invoked: publication must not prompt for it, require it, or record its
absence as a skip. An explicit user request for a live bootstrap acceptance run in the current
conversation authorizes one run.

The runner refuses to start without `-Approved` and refuses known CI environments. `-Approved` is
an assertion that the current user explicitly requested this particular run; it is not a persistent
preference and must not be inferred from an earlier run.

## Current scenario

`clean-bootstrap` describes an intentionally tiny Python standard-library greeting CLI with no web,
identity, persistence, network, deployment, or third-party runtime concerns. The ordinary mode uses
a pre-confirmed intake fixture under `tests/live/scenarios/clean-bootstrap/docs/architecture/`.
Passing `-ExerciseIntakeSkill` instead starts from `PROJECT_REQUEST.md`, adds one paid Codex session,
and requires the installed bootstrap skill to create and validate the confirmed intake before the
same bootstrap workflow runs. This keeps the acceptance target unambiguous while exercising:

1. candidate release packaging;
2. clean Spec Kit initialization and candidate installation through temporary loopback catalogs
   and the real bundle provenance machinery;
3. confirmed-intake validation, capability assessment, and research;
4. the explicit automatic approval and ratification route across all three generated review packets;
5. constitution drafting and ratification;
6. architecture, quality-system, and roadmap generation;
7. bootstrap-context handoffs;
8. final readiness and deterministic governance validation.

On Windows, the installed Python runtime cannot construct its normal HTTPS handler on every host.
For candidate setup only, the harness therefore invokes Specify with a process-scoped opener that
disables HTTPS and rejects every non-loopback HTTP host. The real loopback catalog downloads and
bundle contribution records remain exercised without opening a public-network path.

The stronger intake mode additionally proves that the installed skill converts a raw description
into the canonical project intent, architecture map, Structurizr projection, and confirmed intake;
that deterministic validation accepts those generated artifacts; and that the skill returns the
exact portable one-line workflow command. The harness preserves all intake worker streams and stops
before bootstrap if any part of that seam fails.

The same clean consumer can optionally continue through its first complete feature lifecycle. Pass
`-ContinueFirstSlice` to run `speckit.specify`, `speckit.plan`, `speckit.tasks`, and
`speckit.implement` for the first Ready roadmap entry. This continuation deliberately supplies only
the user intent and pointers to the approved repository artifacts: the installed commands and hooks
must discover and apply the constitution, architecture, roadmap, ownership rules, and lifecycle
evidence themselves. The mandatory clarify, analyze, architecture-check, ownership, and
implementation-check hooks therefore remain part of what the live run proves.

Run it only after an explicit user request:

```powershell
./scripts/Test-LiveBootstrap.ps1 -Integration codex -Approved
```

To exercise the complete conversational front door through bootstrap:

```powershell
./scripts/Test-LiveBootstrap.ps1 -Integration codex -ExerciseIntakeSkill -Approved
```

To include the optional first slice, which launches additional paid sessions and can consume a
second two-hour timeout, install Python 3.13 and run:

```powershell
./scripts/Test-LiveBootstrap.ps1 -Integration codex -ContinueFirstSlice -Approved
```

The runner verifies Python 3.13 before starting any paid worker when this option is selected. Change
the continuation timeout with `-FirstSliceTimeoutSeconds`.

The disposable localhost catalog install retries a transfer only when Spec Kit reports both a
failed extension-archive save and that no changes were recorded. Other setup failures remain
immediate failures so retries cannot conceal a partial installation.

Use `-Integration claude` only when the Claude CLI is installed and the user selected it. The
default timeout is two hours and can be changed with `-TimeoutSeconds`.

## Evidence

Each run is preserved below `artifacts/live-acceptance/<run>/`:

- `report.md` and `report.json`: overall verdict, duration, run ID, failures, warnings, performance
  metrics, and artifact evidence;
- `workflow.stdout.log`: structured Spec Kit workflow outcome;
- `workflow.stderr.log`: live command, agent, and gate output stream;
- `monitor.jsonl`: timestamped workflow step transitions and process ID;
- `setup.log`: release build, initialization, and component-installation output;
- `catalog-server/`: retained candidate catalogs and packages served only over loopback during setup;
- `validation.log`: final approval/readiness governance validation;
- `first-slice.workflow.stdout.log`, `first-slice.workflow.stderr.log`, and
  `first-slice.monitor.jsonl`: the optional full lifecycle and its step transitions;
- `first-slice.validation.log`: independent ownership validation, unittest results, and exact CLI
  output/exit-code checks for the optional implemented slice;
- `first-slice-managed-baseline.json`: before/after hashes proving the continuation did not edit
  installed Program Kit-managed files;
- `project/`: the disposable consumer repository for diagnosis;
- `packages/`: the exact candidate component archives after extraction.

Failed runs are retained. Never delete their evidence automatically; compare their logs and
artifacts before changing the workflow.

## Narrow agent-session exception

Normal consumer initialization and outer bootstrap orchestration must still be launched by the
human from a normal user-owned terminal. The live runner is a source-repository test harness: after
an explicit user request it creates a disposable repository and removes Codex parent-session markers only
from the owned workflow subprocess so the candidate's real nested command steps can execute.
Codex workers receive a `workspace-write` sandbox. The parent workflow also receives a
process-scoped `GIT_CONFIG_*` safe-directory value as a best-effort convenience, but Windows worker
sandboxes may filter that environment before launching the agent. The harness therefore writes
disposable worker guidance requiring every Git command to use the command-scoped form
`git -c safe.directory=<absolute-disposable-project> -c core.excludesFile= <command>` on Windows or
use `/dev/null` as the excludes value on POSIX. Windows Git rejects `NUL` as an excludes file. This is the reliable fallback observed in live
runs: `safe.directory` handles the worker SID, while the null exclude file prevents a harmless
permission warning when the sandbox cannot read the user's global Git ignore file. It never changes
global Git configuration, never persists a safe-directory exception, never installs an approval
rule, and never bypasses the coding agent's sandbox.

The harness sets `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` for its owned workflow process tree, and
the workflow runs its UTF-8 preparation step before the first agent command. This prevents Windows
legacy-console encoding from breaking Unicode diagnostics. Raw agent stderr is written to evidence
without flooding the terminal; the terminal shows concise state transitions.

When launching the harness from a sandboxed Codex Desktop task, allow the outer harness process to
access the installed Codex CLI and its user-owned home. A run that fails immediately with
`Error finding codex home: Could not find home directory` never started a paid worker; preserve its
evidence and retry with external-process permission. Keep the inner `--sandbox workspace-write`
setting unchanged—the outer launch permission is not a reason to weaken disposable workers.

Each workflow stage receives a compact, hash-bound stage brief and a separate evidence index. Stage
prompts read the compact brief first and query only relevant evidence instead of printing every
prior artifact. Token usage, stage duration, stream size, and context size are included in the
report. Their budgets are advisory: they expose regressions without converting a semantically
correct bootstrap into a false failure.
The clean scenario also tracks proportional byte targets for research, architecture, quality, and
readiness artifacts; exceeding one produces a warning, not a failed run.

When the first-slice continuation is selected, the report also records the feature artifacts,
hash-bound clarify/analyze lifecycle evidence, application-test results, exact success and rejected-
argument behavior, and a before/after hash comparison of installed Program Kit-managed files. A
change to those managed files fails the run; legitimate feature-owned source, tests, feature
documents, evidence, and roadmap lifecycle updates remain visible in the preserved repository.

Stage briefs also carry resolved governance paths, exact intended writes, contract references,
validation commands, and byte budgets for every size-sensitive output a stage may edit. Agents must
use these instead of searching `.specify`, dumping catalogs, or reading validator implementation
merely to rediscover an output format, and must recheck budgets after downstream link updates.

This exception must not be generalized. Future scenarios such as mid-bootstrap and mid-spec upgrade
tests belong under `tests/live/scenarios/` and must reuse the same explicit-request, isolation,
logging, and CI-refusal boundary.
