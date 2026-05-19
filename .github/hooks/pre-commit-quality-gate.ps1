#!/usr/bin/env pwsh
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "[hook] pre-commit quality gate"

$isPythonRepo = (Test-Path "pyproject.toml") -or (Test-Path "requirements.txt")
$isNodeRepo = Test-Path "package.json"

if ($isPythonRepo) {
    if (Get-Command ruff -ErrorAction SilentlyContinue) {
        Write-Host "[hook] ruff check ."
        ruff check .
    }

    if (Get-Command mypy -ErrorAction SilentlyContinue) {
        Write-Host "[hook] mypy . (best-effort)"
        mypy .
    }

    if (Get-Command pytest -ErrorAction SilentlyContinue) {
        Write-Host "[hook] pytest -q"
        pytest -q
    }
}

if ($isNodeRepo -and (Get-Command npm -ErrorAction SilentlyContinue)) {
    $npmScripts = (npm run --silent) 2>$null
    if ($npmScripts -match "\blint\b") {
        Write-Host "[hook] npm run lint"
        npm run lint
    }
    if ($npmScripts -match "\btypecheck\b") {
        Write-Host "[hook] npm run typecheck"
        npm run typecheck
    }
}

Write-Host "[hook] quality gate completed"
