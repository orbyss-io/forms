@echo off
setlocal
set "PROGRAM_KIT_REF=v0.9.10"

rem Program Kit consumer bootstrap for a repository that does not already contain Program Kit.
rem Run this file from a normal user-owned PowerShell prompt in the repository root.

if "%~1"=="" (
  echo ERROR: Supply exactly one Spec Kit integration ID, for example: %~nx0 codex 1>&2
  exit /b 2
)
if not "%~2"=="" (
  echo ERROR: Supply exactly one Spec Kit integration ID, for example: %~nx0 codex 1>&2
  exit /b 2
)
set "PROGRAM_KIT_INTEGRATION=%~1"
for /f "delims=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" %%A in ("%PROGRAM_KIT_INTEGRATION%") do (
  echo ERROR: Supply exactly one Spec Kit integration ID, for example: %~nx0 codex 1>&2
  exit /b 2
)

for %%I in ("%~dp0.") do set "PROGRAM_KIT_SCRIPT_DIR=%%~fI"
if /I not "%CD%"=="%PROGRAM_KIT_SCRIPT_DIR%" (
  echo ERROR: Change to the repository root containing %~nx0 before running it. 1>&2
  exit /b 2
)

if defined CODEX_SESSION_ID goto :agent_environment
if defined CODEX_THREAD_ID goto :agent_environment
if defined CODEX_INTERNAL_ORIGINATOR_OVERRIDE goto :agent_environment

if exist ".specify\bundle-records.json" (
  findstr /i /c:"program-kit" ".specify\bundle-records.json" >nul 2>nul
  if not errorlevel 1 goto :already_initialized
)
if exist ".specify\extensions.yml" (
  findstr /i /c:"program-kit-governance" /c:"program-kit-dotnet" ".specify\extensions.yml" >nul 2>nul
  if not errorlevel 1 goto :already_initialized
)
if exist ".specify\workflows\workflow-registry.json" (
  findstr /i /c:"program-kit-bootstrap" ".specify\workflows\workflow-registry.json" >nul 2>nul
  if not errorlevel 1 goto :already_initialized
)
for %%F in (
  ".specify\extension-catalogs.yml"
  ".specify\preset-catalogs.yml"
  ".specify\workflow-catalogs.yml"
  ".specify\bundle-catalogs.yml"
) do (
  if exist "%%~F" (
    findstr /i /c:"program-kit" "%%~F" >nul 2>nul
    if not errorlevel 1 goto :already_initialized
  )
)
if exist ".specify\extensions\program-kit-governance\extension.yml" goto :already_initialized
if exist ".specify\extensions\program-kit-dotnet\extension.yml" goto :already_initialized
if exist ".specify\workflows\program-kit-bootstrap\workflow.yml" goto :already_initialized
if exist ".agents\skills\speckit-program-kit-governance-bootstrap\SKILL.md" goto :already_initialized

where specify >nul 2>nul
if errorlevel 1 (
  echo ERROR: Spec Kit 1.0.1 or a compatible 1.x `specify` command is required. 1>&2
  exit /b 2
)
call specify --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: The `specify` command was found but could not execute successfully. Repair Spec Kit and rerun the initializer. 1>&2
  exit /b 2
)

where git >nul 2>nul
if errorlevel 1 (
  echo ERROR: Git must be available as `git` because coding-agent workflows run inside a Git work tree. 1>&2
  exit /b 2
)
call git --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: The `git` command was found but could not execute successfully. Repair Git and rerun the initializer. 1>&2
  exit /b 2
)
call git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 goto :git_not_initialized

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python must be available as `python` because Program Kit uses the Python Spec Kit runtime. 1>&2
  exit /b 2
)
call python --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: The `python` command was found but could not execute successfully. Repair Python and rerun the initializer. 1>&2
  exit /b 2
)

call python -c "import yaml" >nul 2>nul
if errorlevel 1 (
  call python -m pip --version >nul 2>nul
  if errorlevel 1 goto :pip_missing
  echo Installing the PyYAML dependency required by the Spec Kit Python resolver...
  call python -m pip install --disable-pip-version-check "PyYAML>=6,<7"
  if errorlevel 1 goto :dependency_failed
  call python -c "import yaml" >nul 2>nul
  if errorlevel 1 goto :dependency_failed
)

echo [1/8] Initializing Spec Kit for %PROGRAM_KIT_INTEGRATION% with the Python script flavor...
call specify init . --force --non-interactive --integration %PROGRAM_KIT_INTEGRATION% --script py
if errorlevel 1 goto :failed

echo [2/8] Registering the Program Kit extension catalog...
call specify extension catalog add https://raw.githubusercontent.com/orbyss-io/program-kit/%PROGRAM_KIT_REF%/catalogs/extensions.json --name program-kit --install-allowed
if errorlevel 1 goto :failed

echo [3/8] Registering the Program Kit preset catalog...
call specify preset catalog add https://raw.githubusercontent.com/orbyss-io/program-kit/%PROGRAM_KIT_REF%/catalogs/presets.json --name program-kit --install-allowed
if errorlevel 1 goto :failed

echo [4/8] Registering the Program Kit workflow catalog...
call specify workflow catalog add https://raw.githubusercontent.com/orbyss-io/program-kit/%PROGRAM_KIT_REF%/catalogs/workflows.json --name program-kit
if errorlevel 1 goto :failed

echo [5/8] Registering the Program Kit bundle catalog...
call specify bundle catalog add https://raw.githubusercontent.com/orbyss-io/program-kit/%PROGRAM_KIT_REF%/catalogs/bundles.json --id program-kit --policy install-allowed
if errorlevel 1 goto :failed

echo [6/8] Installing the bootstrap workflow required by Spec Kit 1.0.1...
call specify workflow add program-kit-bootstrap
if errorlevel 1 goto :failed

echo [7/8] Installing Program Kit...
call specify bundle install program-kit --integration %PROGRAM_KIT_INTEGRATION%
if errorlevel 1 goto :failed
call python ".specify\extensions\program-kit-governance\scripts\ensure_utf8.py" --target .
if errorlevel 1 goto :failed

echo [8/8] Switching Program Kit catalogs to the update channel...
call specify extension catalog remove program-kit
if errorlevel 1 goto :failed
call specify preset catalog remove program-kit
if errorlevel 1 goto :failed
call specify workflow catalog remove 0
if errorlevel 1 goto :failed
call specify bundle catalog remove program-kit
if errorlevel 1 goto :failed
call specify extension catalog add https://raw.githubusercontent.com/orbyss-io/program-kit/main/catalogs/extensions.json --name program-kit --install-allowed
if errorlevel 1 goto :failed
call specify preset catalog add https://raw.githubusercontent.com/orbyss-io/program-kit/main/catalogs/presets.json --name program-kit --install-allowed
if errorlevel 1 goto :failed
call specify workflow catalog add https://raw.githubusercontent.com/orbyss-io/program-kit/main/catalogs/workflows.json --name program-kit
if errorlevel 1 goto :failed
call specify bundle catalog add https://raw.githubusercontent.com/orbyss-io/program-kit/main/catalogs/bundles.json --id program-kit --policy install-allowed
if errorlevel 1 goto :failed

echo.
echo Program Kit initialization is complete.
exit /b 0

:agent_environment
echo ERROR: Run %~nx0 yourself from a normal user-owned PowerShell prompt, not from a Codex Desktop task or interactive Codex CLI agent. 1>&2
exit /b 2

:already_initialized
echo ERROR: Program Kit is already installed, or a partial Program Kit installation exists in %CD%. 1>&2
echo Use the documented Program Kit update commands instead of running the initializer again. 1>&2
exit /b 2

:dependency_failed
echo ERROR: PyYAML could not be installed for the `python` command. Install "PyYAML^>=6,^<7" for that interpreter and rerun the initializer. 1>&2
exit /b 2

:pip_missing
echo ERROR: PyYAML is missing and `python -m pip` is unavailable. Install pip for this Python interpreter, then install "PyYAML^>=6,^<7" and rerun the initializer. 1>&2
exit /b 2

:git_not_initialized
echo ERROR: This directory is not inside an initialized Git work tree. 1>&2
echo Run these commands from %CD%, then rerun %~nx0 %PROGRAM_KIT_INTEGRATION%: 1>&2
echo. 1>&2
echo   git init 1>&2
echo   git status 1>&2
exit /b 2

:failed
echo ERROR: Program Kit initialization stopped because a command failed. Review the output above; no execution-policy workaround is required or recommended. 1>&2
exit /b 1
