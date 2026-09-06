# Program Kit setup boundary for Codex on Windows

Run `specify init`, Program Kit bundle or extension installation and updates, and
`specify workflow run program-kit-bootstrap ...` yourself from a normal user-owned PowerShell or WSL
terminal. Do not run them from a Codex Desktop task or an interactive Codex CLI agent.

## Reason

OpenAI documents that native Windows agent mode is sandboxed and that its preferred elevated mode
uses dedicated lower-privilege users plus filesystem permission boundaries. OpenAI also documents
that Codex under WSL runs inside the Linux environment. See
[Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox) and
[WSL](https://learn.chatgpt.com/docs/windows/wsl).

Program Kit has observed that initialization performed by the dedicated Windows sandbox identity
can leave `.agents`, `.specify`, and related paths owned by that identity. A later elevated-sandbox
refresh may fail to establish protective ACLs, including with `SetNamedSecurityInfoW ... error 5`.
Separately, Spec Kit dispatches Codex workflow commands through `codex exec`, so starting the outer
workflow from an existing Codex agent creates unsupported nested agent execution.

An interactive `codex` CLI agent is also sandboxed; it is not a substitute for a normal shell.

## Safe workflow

1. Open PowerShell directly, or WSL when the repository lives in WSL.
2. Change to the repository root. Existing project files and an existing Spec Kit initialization
   are allowed; the initializer stops if Program Kit itself is already or partially installed.
3. Download the root initializer from the matching GitHub release and run it with the required
   Spec Kit integration ID: `Initialize-ProgramKit.sh codex` from Bash in WSL, or
   `Initialize-ProgramKit.cmd codex` from PowerShell on Windows, including under `AllSigned`.
   Pass `claude` instead for Claude Code. The command launcher requires no execution-policy change.
   Every variant verifies that `specify`, `python`, and Git can execute; Spec Kit validates the selected
   integration's coding-agent tooling. When the directory is not already in a Git work tree, the
   launcher stops before package installation or repository setup and prints `git init` and
   `git status` for the user to run. It ensures the exact workflow interpreter can
   import `PyYAML>=6,<7` before repository setup. It selects the Python Spec Kit runtime and
   performs catalog registration and Program Kit installation without an initial design. The Codex
   equivalent
   initialization command is `specify init . --force --non-interactive --integration codex
   --script py`. Never bypass or lower `AllSigned`, broadly unblock repository files, or grant
   unrestricted execution.
4. Start the outer workflow yourself:

   ```text
   specify workflow run program-kit-bootstrap --input "bootstrap_intake=docs/architecture/bootstrap-intake.json" --input "integration=auto"
   ```

   Generate and confirm that fixed intake path through the installed bootstrap skill first. The
   command is one physical line and is portable across ordinary user-owned terminals.

   Codex workers require a Git work tree. For a directory initialized by an older Program Kit
   release without Git, run `git init` and `git status` from the repository root before starting a
   new workflow run. Do not pass `--skip-git-repo-check`.

5. Let Spec Kit launch the sandboxed `codex exec` workers.
6. Review every generated artifact and run each `specify workflow resume ...` from the same normal
   shell. The human supplies every verdict.
7. Use Codex Desktop for ordinary repository work afterward.

When the bootstrap skill is invoked from Codex, it must only display the complete command. It must
not execute it, request an exception, create an approval rule, or start another Codex agent.

Before intake or research, Program Kit inspects the resolver referenced by
`.agents/skills/speckit-constitution/SKILL.md`. On native Windows the resolver must exist and execute.
If the PowerShell flavor is blocked by local signing policy, stop and cleanly regenerate the Codex
integration with `specify init . --force --non-interactive --integration codex --script py`. Confirm
that `.specify/scripts/python/resolve_template.py` exists and that the constitution skill references
it. Do not weaken execution policy, broadly unblock repository files, or grant unrestricted
execution.

If the Python resolver exists but reports that PyYAML is required, install the dependency into the
exact workflow interpreter and verify the resolver directly; do not reinitialize Spec Kit for a
package dependency:

```powershell
python -m pip install --disable-pip-version-check "PyYAML>=6,<7"
python .specify/scripts/python/resolve_template.py constitution-template --json
```

## Existing affected repository

Rerunning `specify init` alone does not repair ownership. Close Codex, back up the user-selected
initial-design file and any other uncommitted work outside the repository, and inspect `git status`,
`git log --oneline`, and `git remote -v` from a normal shell.

Prefer a new user-owned working copy while preserving history:

- Clone the remote with `--no-checkout`, or use `git clone --no-hardlinks --no-checkout` from the
  affected local repository when it contains history not available remotely.
- Copy only the backed-up design file and other reviewed uncommitted work into the new working copy.
- Confirm the normal user owns the new directory and `.git`, and review `git status` before any
  commit.
- Run initialization and Program Kit setup from that normal shell.

If the existing directory must remain, ask its owner or an administrator to restore correct
ownership and inherited DACLs before removing reviewed generated content. Do not grant `Everyone`
write access. Preserve `.git` unless the human explicitly chooses a completely new repository.
