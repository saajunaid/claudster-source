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
#   junai-revert [-Last N] [-Sha SHA[,SHA...]]  revert commits + cascade to all repos
#   junai-export [OutputPath]     export pool to a local folder or zip (no GitHub needed)
#   junai-import SourcePath        import pool from a local folder or zip into current project

$JUNO_POOL = "E:\Projects\junai"
$JUNO_GITHUB = "$JUNO_POOL\.github"
$POOL_FOLDERS = @("agents", "skills", "prompts", "instructions", "diagrams", "tools")

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

    # Deploy .vscode/mcp.json (pre-configured with ${workspaceFolder} — profile-agnostic)
    $mcpSrc = Join-Path $JUNO_POOL ".vscode\mcp.json"
    if (Test-Path $mcpSrc) {
        $vscodeTarget = Join-Path $ProjectRoot ".vscode"
        if (-not (Test-Path $vscodeTarget)) { New-Item -ItemType Directory -Path $vscodeTarget | Out-Null }
        Copy-Item $mcpSrc $vscodeTarget -Force
        Write-Host "  [OK]  .vscode/mcp.json" -ForegroundColor Green
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

    # Commit and push junai
    Push-Location $JUNO_POOL

    $hasChanges = (git status --porcelain) -ne $null
    if (-not $hasChanges) {
        Write-Host ""
        Write-Host "  No changes detected in junai. Nothing to commit." -ForegroundColor DarkGray
        Pop-Location
        return
    }

    # ── PyPI build copy (src/junai_mcp/server.py) ─────────────────────────────
    $poolServer  = Join-Path $JUNO_GITHUB "tools\mcp-server\server.py"
    $pypiServer  = Join-Path $JUNO_POOL   "src\junai_mcp\server.py"
    if ((Test-Path $poolServer) -and (Test-Path $pypiServer)) {
        $poolHash = (Get-FileHash $poolServer  -Algorithm SHA256).Hash
        $pypiHash = (Get-FileHash $pypiServer -Algorithm SHA256).Hash
        if ($poolHash -ne $pypiHash) {
            Copy-Item $poolServer $pypiServer -Force
            Write-Host "  [OK]  src/junai_mcp/server.py  (synced from pool)" -ForegroundColor Green
            Write-Host "  [!!]  server.py changed -- run junai-publish-mcp to bump version + publish to PyPI" -ForegroundColor Yellow
        } else {
            Write-Host "  [--]  src/junai_mcp/server.py  (no change)" -ForegroundColor DarkGray
        }
    }
    # ──────────────────────────────────────────────────────────────────────────

    git add .github/agents .github/skills .github/prompts .github/instructions .github/diagrams .github/tools | Out-Null

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

function junai-publish-mcp {
    # Bumps the version in pyproject.toml and publishes junai-mcp to PyPI.
    # Requires: pip install build twine (once per machine), PyPI credentials configured.
    #
    # Usage:
    #   junai-publish-mcp           # prompts for new version
    #   junai-publish-mcp -Version 0.1.2
    param([string]$Version = "")

    Push-Location $JUNO_POOL

    $pyproject = Join-Path $JUNO_POOL "pyproject.toml"
    if (-not (Test-Path $pyproject)) {
        Write-Host "  pyproject.toml not found at $JUNO_POOL" -ForegroundColor Red
        Pop-Location; return
    }

    $content     = Get-Content $pyproject -Raw
    $currentVer  = [regex]::Match($content, 'version\s*=\s*"([^"]+)"').Groups[1].Value

    Write-Host ""
    Write-Host "  JUNAI PUBLISH MCP  junai-mcp --> PyPI" -ForegroundColor Cyan
    Write-Host "  -----------------------------------------" -ForegroundColor DarkGray
    Write-Host "  Current version: $currentVer" -ForegroundColor DarkGray

    if ([string]::IsNullOrWhiteSpace($Version)) {
        $Version = Read-Host "  New version (blank to keep $currentVer)"
        if ([string]::IsNullOrWhiteSpace($Version)) { $Version = $currentVer }
    }

    if ($Version -ne $currentVer) {
        $content = $content -replace "version\s*=\s*`"$([regex]::Escape($currentVer))`"", "version = `"$Version`""
        Set-Content $pyproject $content -NoNewline
        Write-Host "  [OK]  pyproject.toml bumped $currentVer --> $Version" -ForegroundColor Green
    }

    # Clean old dist/
    $dist = Join-Path $JUNO_POOL "dist"
    if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }

    Write-Host "  Building..." -ForegroundColor DarkGray
    python -m build 2>&1 | Where-Object { $_ -match "Successfully|error|ERROR" } | Write-Host

    Write-Host "  Uploading to PyPI..." -ForegroundColor DarkGray
    twine upload dist\*

    # Commit version bump
    $hasChanges = (git status --porcelain) -ne $null
    if ($hasChanges) {
        git add pyproject.toml
        git commit -m "chore: bump junai-mcp to v$Version" | Out-Null
        git push | Out-Null
        Write-Host "  [OK]  Committed and pushed version bump" -ForegroundColor Green
    }

    Pop-Location
    Write-Host ""
    Write-Host "  Published junai-mcp v$Version to PyPI." -ForegroundColor Cyan
    Write-Host ""
}

function junai-revert {
    # Reverts one or more commits in agent-sandbox and cascades to all downstream
    # repos (junai, junai-vscode). Safe -- new revert commits, no history rewrite.
    #
    # Usage:
    #   junai-revert                              # revert HEAD (last commit)
    #   junai-revert -Last 3                      # revert last 3 commits
    #   junai-revert -Sha abc123                  # revert one specific commit
    #   junai-revert -Sha abc123,def456,ghi789    # revert multiple commits
    #   junai-revert -Last 2 -NoCascade           # revert agent-sandbox only
    param(
        [string[]]$Sha       = @(),
        [int]$Last           = 0,
        [string]$Message     = "",
        [switch]$NoCascade
    )

    $agentSandbox = "E:\Projects\agent-sandbox"

    Push-Location $agentSandbox

    # -- Resolve which SHAs to revert ------------------------------------------
    $resolved = @()

    if ($Sha.Count -gt 0) {
        # Accept comma-separated values passed as a single string element
        $expanded = $Sha | ForEach-Object { $_ -split ',' } |
                           ForEach-Object { $_.Trim() } |
                           Where-Object   { $_ -ne '' }
        foreach ($s in $expanded) {
            $check = git log --oneline -1 $s 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  [ERROR]  Commit not found: $s" -ForegroundColor Red
                Pop-Location; return
            }
            $resolved += $s
        }
    } elseif ($Last -gt 0) {
        $resolved = @(git log --format="%H" -n $Last)
    } else {
        # Default: revert HEAD
        $resolved = @(git log --format="%H" -n 1)
    }

    if ($resolved.Count -eq 0) {
        Write-Host "  [ERROR]  No commits resolved to revert." -ForegroundColor Red
        Pop-Location; return
    }

    # Sort newest-first by walking git log order (avoids conflicts on revert)
    $allHashes  = @(git log --format="%H")
    $resolved   = $allHashes | Where-Object { $resolved -contains $_ }

    # -- Show plan -------------------------------------------------------------
    Write-Host ""
    Write-Host "  JUNAI REVERT" -ForegroundColor Yellow
    Write-Host "  -----------------------------------------" -ForegroundColor DarkGray
    Write-Host "  Commits to revert (newest first):" -ForegroundColor Yellow
    $n = 1
    foreach ($s in $resolved) {
        $line = git log --oneline -1 $s
        Write-Host "    [$n] $line" -ForegroundColor Yellow
        $n++
    }
    Write-Host ""
    if ($NoCascade) {
        Write-Host "  Cascade   : agent-sandbox only (-NoCascade)" -ForegroundColor DarkGray
    } else {
        Write-Host "  Cascade   : agent-sandbox --> junai --> junai-vscode (at next publish)" -ForegroundColor DarkGray
    }
    Write-Host ""

    $confirm = Read-Host "  Proceed? (y/N)"
    if ($confirm -notmatch '^[Yy]$') {
        Write-Host "  Cancelled." -ForegroundColor DarkGray
        Pop-Location; return
    }

    # -- Revert each commit (newest first) -------------------------------------
    foreach ($s in $resolved) {
        git revert --no-edit $s | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [ERROR]  git revert failed on $s -- resolve conflicts manually." -ForegroundColor Red
            Pop-Location; return
        }
        Write-Host "  [OK]  reverted $s" -ForegroundColor Green
    }

    # Apply custom message to the final revert commit if provided
    if (-not [string]::IsNullOrWhiteSpace($Message)) {
        git commit --amend -m $Message | Out-Null
    }

    git push | Out-Null
    Write-Host "  [OK]  agent-sandbox pushed" -ForegroundColor Green

    Pop-Location

    # -- Cascade to downstream repos -------------------------------------------
    if (-not $NoCascade) {
        $revertMsg = "revert: undo $($resolved.Count) commit(s) from agent-sandbox"
        if (-not [string]::IsNullOrWhiteSpace($Message)) { $revertMsg = $Message }

        # 1. junai -- pool folders + server.py SHA check (handled inside junai-push)
        junai-push -Message $revertMsg

        # 2. junai root sync.ps1 -- not inside pool folders, synced separately
        $srcSync  = Join-Path $agentSandbox "sync.ps1"
        $dstSync  = Join-Path $JUNO_POOL    "sync.ps1"
        if (Test-Path $srcSync) {
            $srcHash = (Get-FileHash $srcSync -Algorithm SHA256).Hash
            $dstHash = (Get-FileHash $dstSync -Algorithm SHA256).Hash
            if ($srcHash -ne $dstHash) {
                Copy-Item $srcSync $dstSync -Force
                Push-Location $JUNO_POOL
                git add sync.ps1
                $dirty = (git status --porcelain) -ne $null
                if ($dirty) {
                    git commit -m "$revertMsg (sync.ps1)" | Out-Null
                    git push | Out-Null
                    Write-Host "  [OK]  junai sync.ps1 reverted" -ForegroundColor Green
                }
                Pop-Location
            }
        }

        # 3. junai-vscode -- pool/ is gitignored, rebuilt from agent-sandbox at publish
        Write-Host "  [--]  junai-vscode pool/ is gitignored -- auto-updates at next publish" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "  Done. Revert complete." -ForegroundColor Yellow
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

    # Include .vscode/mcp.json
    $mcpSrc = Join-Path $JUNO_POOL ".vscode\mcp.json"
    if (Test-Path $mcpSrc) {
        $vscodeDst = Join-Path $OutputPath ".vscode"
        if (-not (Test-Path $vscodeDst)) { New-Item -ItemType Directory -Path $vscodeDst | Out-Null }
        Copy-Item $mcpSrc $vscodeDst -Force
        Write-Host "  [OK]  .vscode/mcp.json" -ForegroundColor Green
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
    Write-Host "    junai-import PATH-TO-EXPORT-FOLDER   # from any project root" -ForegroundColor DarkGray
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

    # Deploy .vscode/mcp.json
    $mcpSrc = Join-Path $SourcePath ".vscode\mcp.json"
    if (Test-Path $mcpSrc) {
        $vscodeTarget = Join-Path $ProjectRoot ".vscode"
        if (-not (Test-Path $vscodeTarget)) { New-Item -ItemType Directory -Path $vscodeTarget | Out-Null }
        Copy-Item $mcpSrc $vscodeTarget -Force
        Write-Host "  [OK]  .vscode/mcp.json" -ForegroundColor Green
    }

    if ($tmpExtract -and (Test-Path $tmpExtract)) {
        Remove-Item $tmpExtract -Recurse -Force
    }

    Write-Host ""
    Write-Host "  Done. project-config.md was NOT overwritten." -ForegroundColor DarkGray
    Write-Host "  Remember to create/update copilot-instructions.md for this project." -ForegroundColor DarkGray
    Write-Host ""
}
