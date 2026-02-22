# JUNAI Sync - bidirectional pool sync
# Dot-sourced by PowerShell profile. Provides junai-pull and junai-push globally.
#
# One-time setup (run once per machine):
#   Add-Content $PROFILE "`n. 'E:\Projects\junai\sync.ps1'"
#
# If you previously had juno-ai in your profile, update the path:
#   Old:  . 'E:\Projects\juno-ai\sync.ps1'
#   New:  . 'E:\Projects\junai\sync.ps1'
#
# Usage from any project root:
#   junai-pull                    pull latest pool from junai --> current project
#   junai-push                    push pool from current project --> junai + commit + push
#   junai-export [OutputPath]     export pool to a local folder or zip (no GitHub needed)
#   junai-import <SourcePath>     import pool from a local folder or zip into current project

$JUNO_POOL = "E:\Projects\junai"
$JUNO_GITHUB = "$JUNO_POOL\.github"
$POOL_FOLDERS = @("agents", "skills", "prompts", "instructions", "diagrams")

function junai-pull {
    param([string]$ProjectRoot = (Get-Location).Path)

    $target = Join-Path $ProjectRoot ".github"

    if (-not (Test-Path $target)) {
        Write-Host "No .github/ folder found at $ProjectRoot" -ForegroundColor Red
        Write-Host "Are you in a project root?" -ForegroundColor Yellow
        return
    }

    Write-Host ""
    Write-Host "  JUNAI PULL  junai --> $(Split-Path $ProjectRoot -Leaf)" -ForegroundColor Cyan
    Write-Host "  -----------------------------------------" -ForegroundColor DarkGray

    foreach ($folder in $POOL_FOLDERS) {
        $src = Join-Path $JUNO_GITHUB $folder
        if (Test-Path $src) {
            Copy-Item $src $target -Recurse -Force
            Write-Host "  [OK]  $folder" -ForegroundColor Green
        } else {
            Write-Host "  [--]  $folder - not found in pool, skipped" -ForegroundColor Yellow
        }
    }

    # Deploy tools/ to project root (pipeline runner + MCP server)
    $toolsSrc = Join-Path $JUNO_POOL "tools"
    if (Test-Path $toolsSrc) {
        $toolsTarget = Join-Path $ProjectRoot "tools"
        Copy-Item $toolsSrc $toolsTarget -Recurse -Force
        Write-Host "  [OK]  tools" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "  Done. project-config.md was NOT overwritten." -ForegroundColor DarkGray
    Write-Host ""
}

function junai-push {
    param(
        [string]$ProjectRoot = (Get-Location).Path,
        [string]$Message = ""
    )

    $source = Join-Path $ProjectRoot ".github"

    if (-not (Test-Path $source)) {
        Write-Host "No .github/ folder found at $ProjectRoot" -ForegroundColor Red
        Write-Host "Are you in a project root?" -ForegroundColor Yellow
        return
    }

    Write-Host ""
    Write-Host "  JUNAI PUSH  $(Split-Path $ProjectRoot -Leaf) --> junai" -ForegroundColor Magenta
    Write-Host "  -----------------------------------------" -ForegroundColor DarkGray

    foreach ($folder in $POOL_FOLDERS) {
        $src = Join-Path $source $folder
        if (Test-Path $src) {
            Copy-Item $src $JUNO_GITHUB -Recurse -Force
            Write-Host "  [OK]  $folder" -ForegroundColor Green
        } else {
            Write-Host "  [--]  $folder - not in project, skipped" -ForegroundColor DarkGray
        }
    }

    # Sync tools/ back to junai pool
    $toolsSrc = Join-Path $ProjectRoot "tools"
    if (Test-Path $toolsSrc) {
        Copy-Item $toolsSrc $JUNO_POOL -Recurse -Force
        Write-Host "  [OK]  tools" -ForegroundColor Green
    }

    # Commit and push junai
    Push-Location $JUNO_POOL

    $hasChanges = (git status --porcelain) -ne $null
    if (-not $hasChanges) {
        Write-Host ""
        Write-Host "  No changes detected in junai. Nothing to commit." -ForegroundColor DarkGray
        Pop-Location
        return
    }

    git add .github/agents .github/skills .github/prompts .github/instructions .github/diagrams tools | Out-Null

    if ([string]::IsNullOrWhiteSpace($Message)) {
        $projectName = Split-Path $ProjectRoot -Leaf
        $today = Get-Date -Format "yyyy-MM-dd"
        $Message = "feat: sync pool from $projectName - $today"
    }

    git commit -m $Message | Out-Null
    git push | Out-Null

    Pop-Location

    Write-Host ""
    Write-Host "  Committed and pushed to junai." -ForegroundColor Magenta
    Write-Host ""
}

function junai-export {
    # Exports the AI resource pool to a self-contained local folder or zip.
    # Use this when the target machine has no GitHub access.
    #
    # Usage:
    #   junai-export                          # exports to .\junai-pool-export\
    #   junai-export -OutputPath C:\USB\junai  # exports to specific path
    #   junai-export -Zip                     # exports to .\junai-pool-export.zip
    param(
        [string]$OutputPath = (Join-Path (Get-Location).Path "junai-pool-export"),
        [switch]$Zip
    )

    $date = Get-Date -Format "yyyy-MM-dd"
    $zipPath = "$OutputPath-$date.zip"

    if ($Zip) {
        $OutputPath = Join-Path ([System.IO.Path]::GetTempPath()) "junai-pool-export-tmp"
    }
    New-Item -ItemType Directory -Path $OutputPath | Out-Null

    Write-Host ""
    Write-Host "  JUNAI EXPORT  junai --> $OutputPath" -ForegroundColor Cyan
    Write-Host "  -----------------------------------------" -ForegroundColor DarkGray

    foreach ($folder in $POOL_FOLDERS) {
        $src = Join-Path $JUNO_GITHUB $folder
        if (Test-Path $src) {
            Copy-Item $src $OutputPath -Recurse -Force
            Write-Host "  [OK]  $folder" -ForegroundColor Green
        } else {
            Write-Host "  [--]  $folder - not found, skipped" -ForegroundColor Yellow
        }
    }

    # Include tools/
    $toolsSrc = Join-Path $JUNO_POOL "tools"
    if (Test-Path $toolsSrc) {
        Copy-Item $toolsSrc $OutputPath -Recurse -Force
        Write-Host "  [OK]  tools" -ForegroundColor Green
    }

    # Include the sync script itself so the target can dot-source it
    Copy-Item (Join-Path $JUNO_POOL "sync.ps1") $OutputPath -Force
    Write-Host "  [OK]  sync.ps1" -ForegroundColor Green

    if ($Zip) {
        Compress-Archive -Path "$OutputPath\*" -DestinationPath $zipPath -Force
        Remove-Item $OutputPath -Recurse -Force
        Write-Host ""
        Write-Host "  Exported to: $zipPath" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "  Exported to: $OutputPath" -ForegroundColor Cyan
    }

    Write-Host "  On the target machine, run:" -ForegroundColor DarkGray
        Write-Host "    junai-import <path-to-export-folder>   # from any project root" -ForegroundColor DarkGray
    Write-Host ""
}

function junai-import {
    # Imports AI resource pool from a local export folder (created by juno-export).
    # Use this on machines with no GitHub access.
    #
    # Usage (run from the target project root):
    #   junai-import C:\USB\junai-pool-export
    #   junai-import C:\USB\junai-pool-export-2026-02-20.zip
    param(
        [Parameter(Mandatory)][string]$SourcePath,
        [string]$ProjectRoot = (Get-Location).Path
    )

    $target = Join-Path $ProjectRoot ".github"

    if (-not (Test-Path $target)) {
        Write-Host "No .github/ folder found at $ProjectRoot" -ForegroundColor Red
        Write-Host "Are you in a project root?" -ForegroundColor Yellow
        return
    }

    # Handle zip input
    $tmpExtract = $null
    if ($SourcePath -match '\.zip$') {
        $tmpExtract = Join-Path ([System.IO.Path]::GetTempPath()) "junai-import-tmp"
        if (Test-Path $tmpExtract) { Remove-Item $tmpExtract -Recurse -Force }
        Expand-Archive -Path $SourcePath -DestinationPath $tmpExtract
        $SourcePath = $tmpExtract
    }

    if (-not (Test-Path $SourcePath)) {
        Write-Host "Source path not found: $SourcePath" -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "  JUNAI IMPORT  $SourcePath --> $(Split-Path $ProjectRoot -Leaf)" -ForegroundColor Cyan
    Write-Host "  -----------------------------------------" -ForegroundColor DarkGray

    foreach ($folder in $POOL_FOLDERS) {
        $src = Join-Path $SourcePath $folder
        if (Test-Path $src) {
            Copy-Item $src $target -Recurse -Force
            Write-Host "  [OK]  $folder" -ForegroundColor Green
        } else {
            Write-Host "  [--]  $folder - not in export, skipped" -ForegroundColor Yellow
        }
    }

    # Deploy tools/ to project root
    $toolsSrc = Join-Path $SourcePath "tools"
    if (Test-Path $toolsSrc) {
        $toolsTarget = Join-Path $ProjectRoot "tools"
        Copy-Item $toolsSrc $toolsTarget -Recurse -Force
        Write-Host "  [OK]  tools" -ForegroundColor Green
    }

    if ($tmpExtract -and (Test-Path $tmpExtract)) {
        Remove-Item $tmpExtract -Recurse -Force
    }

    Write-Host ""
    Write-Host "  Done. project-config.md was NOT overwritten." -ForegroundColor DarkGray
    Write-Host "  Remember to create/update copilot-instructions.md for this project." -ForegroundColor DarkGray
    Write-Host ""
}
