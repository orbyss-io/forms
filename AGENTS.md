# Program Kit contributor instructions

## Local Firefox limitation

Firefox is not runnable on the current local Windows host. Playwright reaches
`browserType.launch: spawn UNKNOWN` when it tries to start the installed Firefox binary. Do not
retry Firefox repeatedly, diagnose that host error as a product regression, or change production
code to accommodate it. Where a validator exposes `--engines`, use the non-Firefox engines locally
(for example, `--engines=chromium,webkit`), continue the remaining deterministic validators, and
report the known local-host limitation. Keep Firefox in the CI browser matrix; CI remains the
authority for Firefox acceptance.

## Optional live acceptance

The paid live bootstrap acceptance suite is entirely user-invoked. Do not ask whether to run it
during publication, and do not report it as skipped when it was not requested. Deterministic local
and CI-compatible release tests remain mandatory.

- Run `./scripts/Test-LiveBootstrap.ps1 -Integration codex -Approved` (or the explicitly requested
  installed integration) only when the user explicitly requests a live bootstrap acceptance run in
  the current conversation. That request authorizes that run.
- Wait for completion, inspect the generated report and output streams, repair in-scope defects,
  and rerun when needed before reporting the result.
- Never add the paid live suite to CI or run it from an unattended hook.
- Never pass `-Approved` without an explicit user request for the live run in the current
  conversation.
- Pass `-ContinueFirstSlice` only when that request explicitly includes the paid first-slice
  continuation; approval for a bootstrap-only run does not authorize the additional agent sessions.

The live harness is the sole exception to the normal rule against agent-started outer Codex
bootstrap orchestration. It may exercise that exception only for its generated disposable test
repository and preserves evidence under `artifacts/live-acceptance/`. Do not copy its environment
sanitization into consumer setup, bootstrap guidance, or another script.

## Failed stable-release recovery

A pushed stable tag is a release candidate until the complete Release workflow succeeds. NuGet and
host-image publication must remain downstream reusable jobs of that workflow, after all deterministic
validation and public component-release gates. Never restore independent stable-tag triggers for
those irreversible publication workflows.

If the Release workflow fails for a stable tag:

1. Preserve and inspect the failed run evidence.
2. Repair the failure and complete the deterministic local release validation.
3. Obtain or confirm the user's approval for the exact corrected commit and same stable tag.
4. Delete the failed tag locally and remotely, recreate it at the approved corrected commit, and push
   the corrected commit and recreated tag. Do not increment the stable version merely because the
   failed candidate tag existed.
5. Do not tell consumers that the version is available, or unblock dependent work, until the recreated
   tag's complete Release workflow succeeds.

Before repointing, verify whether any immutable registry artifact escaped the gate. Disclose any
partial publication explicitly; a tag correction must never conceal that an artifact was produced
from a different source state.

## Windows live-worker execution

The live harness launches disposable Codex workers with `--sandbox workspace-write`. On Windows,
the worker sandbox can use a different SID from the process that created the disposable Git
repository. A workflow-process `GIT_CONFIG_*` safe-directory injection is only a best-effort aid:
the sandbox may filter it before the worker starts.

The harness therefore writes an `AGENTS.md` inside the disposable consumer. Workers must run every
Git operation as `git -c safe.directory=<absolute-disposable-project> -c core.excludesFile=
<command>` on Windows, or use `/dev/null` as the excludes value on POSIX. Windows Git rejects `NUL`
as an excludes file. The second override prevents a harmless warning
when the sandbox cannot read the user's global Git ignore file. Never use `git config --global`,
never persist a safe-directory exception, and never disable or bypass the sandbox. Keep Python
output UTF-8 (`PYTHONUTF8=1`); the harness and workflow establish this for their owned process trees.

The full worker output is evidence, not console progress. Preserve it in `workflow.stderr.log` and
show concise workflow step transitions in the terminal. Treat token, stream-size, duration, and
stage-brief budgets as advisory performance signals; functional completion and governance
validation remain the pass/fail contract.

When the harness itself is started from a sandboxed Codex Desktop task, the outer task sandbox may
hide the user-owned Codex home and produce `Error finding codex home: Could not find home directory`
before an agent session starts. Retry the explicitly approved harness with external-process access
to the installed Codex CLI. This only relaxes the outer harness launch; it must not remove the
inner disposable workers' `workspace-write` sandbox or broaden their filesystem permissions.
