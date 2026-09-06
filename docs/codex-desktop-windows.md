# Program Kit bootstrap from Windows and Codex

Program Kit requires the human to start repository initialization, Program Kit installation
or update, and outer workflow orchestration from a normal user-owned PowerShell or WSL shell. Do not
ask a Codex Desktop task or an interactive Codex CLI agent to perform those operations.

On affected Windows hosts, Spec Kit 1.0.4 remote catalog updates launched inside Codex Desktop can
also abort with `OPENSSL_Uplink(...): no OPENSSL_Applink` because Codex-owned native dependency
directories precede the uv-installed CLI's OpenSSL runtime on `PATH`. This transport defect is being
routed upstream. Do not sanitize or replace the Codex process `PATH` as a Program Kit workaround.
Use the verified full release archive and its offline `scripts/upgrade_program_kit.py` from a normal
user-owned terminal.

The release-owned updater also recognizes a uv-generated `specify.exe` whose managed Python cannot
execute inside the current Windows sandbox. When that launcher's uv environment remains readable,
the updater validates the embedded interpreter path and uv metadata, then performs read-only probes
through `scripts/invoke_specify.py` using the updater's already-running Python. This reuses the exact
installed `specify_cli` package without downloading, copying, or replacing it. If the package is not
readable or compatible, `PKU114` stops before mutation and prints the exact PowerShell retry command
for a normal user-owned terminal. A persisted repository command vector would retain a stale external
uv path and is therefore not used as a portability claim.

## Why this boundary exists

Official OpenAI documentation says native Windows agent mode runs in a sandbox. The preferred
`elevated` implementation uses dedicated lower-privilege sandbox users and filesystem permission
boundaries; WSL runs Codex inside its Linux environment instead. See the official
[Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox) and
[WSL](https://learn.chatgpt.com/docs/windows/wsl) documentation.

Program Kit's consumer investigation found two independent problems when a Codex agent starts the
outer Spec Kit lifecycle:

1. `specify init` and bundle or extension setup can create `.agents`, `.specify`, and related paths
   as the dedicated Windows sandbox identity. On later turns, the native elevated sandbox may be
   unable to replace those paths' protective ACLs because the invoking Windows user is not their
   owner. The visible failure can include `SetNamedSecurityInfoW ... error 5` and
   `setup refresh had errors`.
2. Spec Kit's Codex integration dispatches workflow command steps by starting `codex exec`. Starting
   `specify workflow run program-kit-bootstrap` from an existing Desktop or CLI agent therefore asks
   a sandboxed agent to start another Codex worker.

Starting an interactive `codex` CLI agent and asking that agent to orchestrate setup is not a normal
shell alternative. The CLI agent is sandboxed too.

## Supported sequence

Use a normal terminal owned by the human account:

1. Open PowerShell directly, or open a WSL shell when the repository and toolchain live in WSL.
2. Change to the repository root. Existing project files and an existing Spec Kit initialization
   are allowed; the initializer stops if Program Kit itself is already or partially installed.
3. Download the appropriate root initializer from the matching GitHub release and run it there:

   - `Initialize-ProgramKit.sh codex` from Bash in WSL; or
   - `Initialize-ProgramKit.cmd codex` from PowerShell on Windows, including under `AllSigned`.

   The required argument is the Spec Kit integration ID; for example, pass `claude` for Claude
   Code. The command launcher works without changing PowerShell execution policy. Both variants
   verify that `specify`, `python`, and Git can execute. Spec Kit validates the selected integration's
   coding-agent tooling. If the directory is not already in a Git work tree, the initializer stops
   before package installation or repository setup and prints `git init` and `git status` for the
   user to run. It also verifies that the exact `python` used by the workflow can import
   PyYAML, installing `PyYAML>=6,<7` through that interpreter's pip only when it is missing. A
   missing or unusable dependency stops initialization before repository setup. Both variants then
   perform the complete installation without deleting unrelated project files, and their Codex
   initialization is equivalent to:

   ```powershell
   specify init . --force --non-interactive --integration codex --script py
   ```

   For a manual installation, use the same `--script py` option before catalog registration and
   Program Kit installation. Program Kit requires Python and uses this resolver consistently. Do
   not bypass or lower `AllSigned`, broadly unblock repository files, or grant unrestricted
   execution.
4. Run `specify workflow run program-kit-bootstrap ...` there.
5. Let Spec Kit launch its `codex exec` workflow workers. Those workers remain sandboxed.
6. Run each human-reviewed `specify workflow resume ...` command from the same normal shell.
7. Use Codex Desktop afterward for ordinary repository work and the installed skills.

Example outer command:

```text
specify workflow run program-kit-bootstrap --input "bootstrap_intake=docs/architecture/bootstrap-intake.json" --input "integration=auto"
```

Generate and confirm the fixed intake contract through the installed bootstrap skill first. The
skill always emits this as one physical line that can be pasted into any normal terminal.
Developers who review the complete result after the run can explicitly add
`--input auto_approve_and_ratify=true`. This bypasses all three pauses but still writes and validates
their review packets and marks the resulting governance evidence as automatic. The option defaults
to `false`; without it, run each human-reviewed `specify workflow resume ...` command as usual.

Codex workflow workers require the repository root to be in a Git work tree. If an older Program
Kit initializer was used in a directory without Git, repair it from the repository root before
starting a new workflow run:

```powershell
git init
git status
```

Do not pass `--skip-git-repo-check`; initialize the repository cleanly instead.

If the installed bootstrap skill is invoked inside Codex, it only formats this command and tells the
user where to run it. It must not execute the command, request an agent exception, or create a
persistent approval rule.

Before intake or research, Program Kit reads `.agents/skills/speckit-constitution/SKILL.md` to
identify the installed Spec Kit resolver. On native Windows it verifies that the referenced file
exists and can execute. A blocked PowerShell resolver stops the workflow immediately. Cleanly
regenerate the Codex integration with `specify init . --force --non-interactive --integration codex
--script py`, then verify that `.specify/scripts/python/resolve_template.py` exists and is referenced
by the constitution skill. Do not weaken execution policy, broadly unblock repository files, or
grant unrestricted execution.

If the referenced Python resolver exists but reports that PyYAML is required, do not reinitialize
Spec Kit. Install the dependency into the exact interpreter used by the workflow and verify it:

```powershell
python -m pip install --disable-pip-version-check "PyYAML>=6,<7"
python .specify/scripts/python/resolve_template.py constitution-template --json
```

## Clean start after agent-owned initialization

Rerunning `specify init` is not an ownership repair. If `.agents`, `.specify`, the repository root,
or files below them are already owned by a sandbox identity, repair ownership and the DACL first or
recreate the working copy under the normal user account.

Before changing anything:

1. Close Codex tasks using the repository.
2. Copy the confirmed intake contract, its bound architecture artifacts, and any other uncommitted work to a safe location
   outside the affected tree.
3. From a normal PowerShell terminal, record `git status`, `git log --oneline`, and
   `git remote -v`.
4. Preserve `.git` unless the human explicitly chooses to discard all repository history.

The conservative option is a clean user-owned working copy:

1. Create a new sibling directory from normal PowerShell or WSL.
2. If the history is available from a remote, clone that remote with `--no-checkout`. If the only
   copy of the history is local, clone the affected repository with `--no-hardlinks --no-checkout`.
   Both approaches preserve Git history while avoiding a checkout of agent-created files.
3. Copy only the backed-up design file and other reviewed uncommitted work into the new working copy.
4. Confirm the new directory, `.git`, and design file are owned by the normal user. Review `git
   status`; do not commit any reported deletions until they are intentional and understood.
5. Run initialization and Program Kit setup from that same normal shell.

If the existing directory must be retained, have the owner or an administrator restore ownership
and appropriate inherited permissions for the repository before removing generated paths. ACL
requirements vary by machine and enterprise policy, so do not apply a blanket `Everyone` grant or
copy an ACL recipe without review. After repair, retain `.git` and the user-selected design file, remove only
the generated content the human has reviewed, and restart setup from the normal shell.

Creating an entirely new Git repository is a separate, destructive choice. Do that only when the
human explicitly decides the old history is unnecessary.

## Do not mask the problem

Do not make `%USERPROFILE%\.codex` writable to a sandbox identity, copy Codex authentication or
state into a repository, globally enable unrestricted agent access, add a rule allowing the outer
workflow, or ask an agent to execute it outside its sandbox. Those approaches do not correct
agent-owned project paths and blur the intended trust boundary.
