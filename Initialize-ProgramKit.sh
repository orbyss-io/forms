#!/usr/bin/env bash
set -euo pipefail

PROGRAM_KIT_REF="v0.9.11"

# Run from a normal user-owned Bash shell in Linux, macOS, or WSL.
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
current_root="$(pwd -P)"
script_name="$(basename -- "${BASH_SOURCE[0]}")"

if [[ $# -ne 1 || ! "$1" =~ ^[A-Za-z0-9_-]+$ ]]; then
  printf 'ERROR: Supply exactly one Spec Kit integration ID, for example: %s codex\n' "$script_name" >&2
  exit 2
fi
program_kit_integration="$1"

if [[ "$current_root" != "$script_dir" ]]; then
  printf 'ERROR: Change to the repository root containing %s before running it.\n' "$script_name" >&2
  exit 2
fi

if [[ -n "${CODEX_SESSION_ID:-}" || -n "${CODEX_THREAD_ID:-}" || -n "${CODEX_INTERNAL_ORIGINATOR_OVERRIDE:-}" ]]; then
  printf 'ERROR: Run %s yourself from a normal user-owned Bash shell, not from a Codex Desktop task or interactive Codex CLI agent.\n' "$script_name" >&2
  exit 2
fi

has_program_kit_catalog() {
  local catalog_config
  for catalog_config in \
    ".specify/extension-catalogs.yml" \
    ".specify/preset-catalogs.yml" \
    ".specify/workflow-catalogs.yml" \
    ".specify/bundle-catalogs.yml"; do
    if [[ -f "$catalog_config" ]] && grep -q 'program-kit' "$catalog_config"; then
      return 0
    fi
  done
  return 1
}

if {
  [[ -f ".specify/bundle-records.json" ]] &&
    grep -Eq '"bundle_id"[[:space:]]*:[[:space:]]*"program-kit"' ".specify/bundle-records.json"
} || {
  [[ -f ".specify/extensions.yml" ]] &&
    grep -Eq 'program-kit-(governance|dotnet)' ".specify/extensions.yml"
} || {
  [[ -f ".specify/workflows/workflow-registry.json" ]] &&
    grep -q 'program-kit-bootstrap' ".specify/workflows/workflow-registry.json"
} || has_program_kit_catalog \
  || [[ -f ".specify/extensions/program-kit-governance/extension.yml" ]] \
  || [[ -f ".specify/extensions/program-kit-dotnet/extension.yml" ]] \
  || [[ -f ".specify/workflows/program-kit-bootstrap/workflow.yml" ]] \
  || [[ -f ".agents/skills/speckit-program-kit-governance-bootstrap/SKILL.md" ]]; then
  printf 'ERROR: Program Kit is already installed, or a partial Program Kit installation exists in %s.\n' "$current_root" >&2
  printf 'Use the documented Program Kit update commands instead of running the initializer again.\n' >&2
  exit 2
fi

if ! command -v specify >/dev/null 2>&1; then
  printf 'ERROR: Spec Kit 1.0.1 or a compatible 1.x specify command is required.\n' >&2
  exit 2
fi
if ! specify --version >/dev/null 2>&1; then
  printf 'ERROR: The specify command was found but could not execute successfully. Repair Spec Kit and rerun the initializer.\n' >&2
  exit 2
fi
if ! command -v git >/dev/null 2>&1; then
  printf 'ERROR: Git must be available as git because coding-agent workflows run inside a Git work tree.\n' >&2
  exit 2
fi
if ! git --version >/dev/null 2>&1; then
  printf 'ERROR: The git command was found but could not execute successfully. Repair Git and rerun the initializer.\n' >&2
  exit 2
fi
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf 'ERROR: This directory is not inside an initialized Git work tree.\n' >&2
  printf 'Run these commands from %s, then rerun %s %s:\n\n' "$current_root" "$script_name" "$program_kit_integration" >&2
  printf '  git init\n' >&2
  printf '  git status\n' >&2
  exit 2
fi
if ! command -v python >/dev/null 2>&1; then
  printf 'ERROR: Python must be available as python because Program Kit uses the Python Spec Kit runtime.\n' >&2
  exit 2
fi
if ! python --version >/dev/null 2>&1; then
  printf 'ERROR: The python command was found but could not execute successfully. Repair Python and rerun the initializer.\n' >&2
  exit 2
fi
if ! python -c 'import yaml' >/dev/null 2>&1; then
  if ! python -m pip --version >/dev/null 2>&1; then
    printf 'ERROR: PyYAML is missing and python -m pip is unavailable. Install pip for this Python interpreter, then install PyYAML>=6,<7 and rerun the initializer.\n' >&2
    exit 2
  fi
  printf 'Installing the PyYAML dependency required by the Spec Kit Python resolver...\n'
  if ! python -m pip install --disable-pip-version-check 'PyYAML>=6,<7'; then
    printf 'ERROR: PyYAML could not be installed for the python command. Install PyYAML>=6,<7 for that interpreter and rerun the initializer.\n' >&2
    exit 2
  fi
  if ! python -c 'import yaml' >/dev/null 2>&1; then
    printf 'ERROR: PyYAML is still unavailable to the python command after installation.\n' >&2
    exit 2
  fi
fi
catalog_root="https://raw.githubusercontent.com/orbyss-io/program-kit/${PROGRAM_KIT_REF}/catalogs"

printf '[1/8] Initializing Spec Kit for %s with the Python script flavor...\n' "$program_kit_integration"
specify init . --force --non-interactive --integration "$program_kit_integration" --script py

printf '[2/8] Registering the Program Kit extension catalog...\n'
specify extension catalog add "${catalog_root}/extensions.json" --name program-kit --install-allowed

printf '[3/8] Registering the Program Kit preset catalog...\n'
specify preset catalog add "${catalog_root}/presets.json" --name program-kit --install-allowed

printf '[4/8] Registering the Program Kit workflow catalog...\n'
specify workflow catalog add "${catalog_root}/workflows.json" --name program-kit

printf '[5/8] Registering the Program Kit bundle catalog...\n'
specify bundle catalog add "${catalog_root}/bundles.json" --id program-kit --policy install-allowed

printf '[6/8] Installing the bootstrap workflow required by Spec Kit 1.0.1...\n'
specify workflow add program-kit-bootstrap

printf '[7/8] Installing Program Kit...\n'
specify bundle install program-kit --integration "$program_kit_integration"
python .specify/extensions/program-kit-governance/scripts/ensure_utf8.py --target .

printf '[8/8] Switching Program Kit catalogs to the update channel...\n'
specify extension catalog remove program-kit
specify preset catalog remove program-kit
specify workflow catalog remove 0
specify bundle catalog remove program-kit
specify extension catalog add 'https://raw.githubusercontent.com/orbyss-io/program-kit/main/catalogs/extensions.json' --name program-kit --install-allowed
specify preset catalog add 'https://raw.githubusercontent.com/orbyss-io/program-kit/main/catalogs/presets.json' --name program-kit --install-allowed
specify workflow catalog add 'https://raw.githubusercontent.com/orbyss-io/program-kit/main/catalogs/workflows.json' --name program-kit
specify bundle catalog add 'https://raw.githubusercontent.com/orbyss-io/program-kit/main/catalogs/bundles.json' --id program-kit --policy install-allowed

printf '\nProgram Kit initialization is complete.\n'
