@echo off
:: junai.bat — JUNAI unified CLI wrapper
::
:: Usage:
::   junai pipeline status
::   junai pipeline init    --project "My Project" --feature "Feature Name"
::   junai pipeline mode    --value supervised|auto
::   junai pipeline gate    --name <gate_name>
::   junai pipeline next    [--event <event>]
::   junai pipeline advance --event <event> [--stage <stage>]
::   junai pipeline transitions
::   junai pipeline preflight --target-stage <stage>
::
::   junai agent make      --name <xyz> [--role executing|advisory]
::   junai agent validate  --name <xyz>
::   junai agent diff      --name <xyz>
::   junai agent onboard   --name <xyz> [--yes]
::   junai agent list
::   junai agent inspect   --name <xyz>
::   junai agent remove    --name <xyz> [--force]

set "SCRIPT_DIR=%~dp0"
set "RUNNER=%SCRIPT_DIR%tools\pipeline-runner\junai.py"
set "PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [junai] ERROR: Python venv not found at %PYTHON%
    echo         Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

if not exist "%RUNNER%" (
    echo [junai] ERROR: junai.py not found at %RUNNER%
    exit /b 1
)

"%PYTHON%" "%RUNNER%" %*
