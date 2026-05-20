# JUNAI Sync - bidirectional pool sync
# Dot-sourced by PowerShell profile. Provides junai-pull and junai-push globally.
#
# One-time setup (run once per machine):
#   Add-Content $PROFILE "`n. 'E:\Projects\agent-sandbox\sync.ps1'"
#
# If you previously had juno-ai in your profile, update the path:
#   Old:  . 'E:\Projects\juno-ai\sync.ps1'
#   New:  . 'E:\Projects\agent-sandbox\sync.ps1'
#
# Usage from any project root:
#   junai-pull                    pull latest pool from junai --> current project
#   junai-push                    push pool from current project --> junai + commit + push (+ auto-publish when keys exist)
#   junai-push -NoPublish         push only (skip publish)
#   junai-release                 publish MCP + VS Code extension using keyfiles
#   junai-release -SkipMcp        extension only
#   junai-release -SkipExtension  MCP only
#   junai-revert [-Last N] [-Sha SHA[,SHA...]]  revert commits + cascade to all repos
#   junai-export [OutputPath]     export pool to a local folder or zip (no GitHub needed)
#   junai-import SourcePath        import pool from a local folder or zip into current project

$REPO_ROOT = $PSScriptRoot
$EXT_REPOS_ROOT = Join-Path $REPO_ROOT "vscode-extensions"
$JUNO_POOL = Join-Path $EXT_REPOS_ROOT "junai"
$JUNO_GITHUB = "$JUNO_POOL\.github"
$JUNAI_VSCODE = Join-Path $EXT_REPOS_ROOT "junai-vscode"
$PTARMIGAN_REPO = Join-Path $EXT_REPOS_ROOT "ptarmigan"
$LIFFEY_REPO = Join-Path $EXT_REPOS_ROOT "liffey"
$JUNAI_ENV_FILE = Join-Path $REPO_ROOT ".env"
$PYPI_KEY_FILE = Join-Path $JUNO_POOL "pypimcp.key"
$VSCE_PAT_FILE = Join-Path $JUNAI_VSCODE "vscode.pat"
$PTARMIGAN_PAT_FILE = Join-Path $PTARMIGAN_REPO "ptarmigan.pat"
$script:JunaiEnvLoaded = $false
$script:JunaiEnv = @{}
# NOTE: "plans" intentionally REMOVED from $POOL_FOLDERS as of 2026-04-27 (Phase 1.0
# stop-the-bleed). Plans are tracked in agent-sandbox only; they never sync to the
# public mirror. Do not re-add without explicit privacy review.
$POOL_FOLDERS = @("agents", "skills", "prompts", "instructions", "hooks", "diagrams", "tools", "recipes", "agent-docs", "handoffs")
$POOL_FILES = @("runtime-targets.json")
$ROOT_PUSH_FILES = @("export_runtime_resources.py", "validate_agents.py", "validate_pool.py", "sync.ps1", ".env.example")
# Top-level repo-root folders that must NEVER be synced to the public mirror.
# vmie/ holds private, organisation-specific resources for local copy-paste only.
$PRIVATE_ROOT_FOLDERS = @("vmie")
# Fully-managed folders: wiped before copy so renamed/moved/deleted files don't persist
$CLEAN_FOLDERS = @("agents", "skills", "prompts", "instructions", "hooks", "tools", "recipes")

function Remove-JunaiCacheDirs {
    param(
        [Parameter(Mandatory)][string]$RootPath,
        [string]$Label = ""
    )

    if (-not (Test-Path $RootPath)) { return }

    $cacheNames = @("__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", "htmlcov")
    $cacheDirs = Get-ChildItem $RootPath -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $cacheNames -contains $_.Name }

    foreach ($dir in $cacheDirs) {
        Remove-Item $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }

    if ($cacheDirs.Count -gt 0) {
        if ([string]::IsNullOrWhiteSpace($Label)) { $Label = $RootPath }
        Write-Host "  [OK]  cache sweep ($Label): removed $($cacheDirs.Count) generated cache folder(s)" -ForegroundColor Green
    }
}

function Initialize-JunaiEnv {
    if ($script:JunaiEnvLoaded) { return }

    $script:JunaiEnv = @{}
    if (Test-Path $JUNAI_ENV_FILE) {
        foreach ($line in Get-Content $JUNAI_ENV_FILE) {
            $trimmed = $line.Trim()
            if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
                continue
            }

            $parts = $trimmed.Split("=", 2)
            if ($parts.Count -ne 2) {
                continue
            }

            $name = $parts[0].Trim()
            if ([string]::IsNullOrWhiteSpace($name)) {
                continue
            }

            $value = $parts[1].Trim()
            if ($value.Length -ge 2) {
                if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                    $value = $value.Substring(1, $value.Length - 2)
                }
            }

            $script:JunaiEnv[$name] = $value
        }
    }

    $script:JunaiEnvLoaded = $true
}

function Get-JunaiEnvValue {
    param([Parameter(Mandatory)][string]$Name)

    Initialize-JunaiEnv

    foreach ($scope in @("Process", "User", "Machine")) {
        $value = [Environment]::GetEnvironmentVariable($Name, $scope)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value.Trim()
        }
    }

    if ($script:JunaiEnv.ContainsKey($Name) -and -not [string]::IsNullOrWhiteSpace($script:JunaiEnv[$Name])) {
        return $script:JunaiEnv[$Name].Trim()
    }

    return ""
}

function Get-JunaiSecretValue {
    param(
        [Parameter(Mandatory)][string]$EnvName,
        [string]$LegacyFilePath = ""
    )

    $value = Get-JunaiEnvValue -Name $EnvName
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        return $value
    }

    if (-not [string]::IsNullOrWhiteSpace($LegacyFilePath) -and (Test-Path $LegacyFilePath)) {
        return (Get-Content $LegacyFilePath -Raw).Trim()
    }

    return ""
}

function Get-PackageJsonVersion {
    param([Parameter(Mandatory)][string]$PackageJsonPath)

    if (-not (Test-Path $PackageJsonPath)) {
        return ""
    }

    $content = Get-Content $PackageJsonPath -Raw
    $match = [regex]::Match($content, '"version"\s*:\s*"([^"]+)"')
    if (-not $match.Success) {
        return ""
    }

    return $match.Groups[1].Value
}

function Get-NextPatchVersion {
    param([Parameter(Mandatory)][string]$VersionString)

    if ($VersionString -notmatch '^(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)$') {
        throw "Unsupported version format: $VersionString"
    }

    $major = [int]$Matches.major
    $minor = [int]$Matches.minor
    $patch = [int]$Matches.patch + 1
    return "$major.$minor.$patch"
}

function Set-PackageJsonVersion {
    param(
        [Parameter(Mandatory)][string]$PackageJsonPath,
        [Parameter(Mandatory)][string]$VersionString
    )

    $content = Get-Content $PackageJsonPath -Raw
    $updated = [regex]::Replace($content, '"version"\s*:\s*"[^"]+"', ('"version": "' + $VersionString + '"'), 1)
    if ($updated -eq $content) {
        throw "Could not update version in $PackageJsonPath"
    }

    Set-Content $PackageJsonPath $updated -NoNewline
}

function Bump-PackageJsonPatchVersion {
    param(
        [Parameter(Mandatory)][string]$RepoPath,
        [Parameter(Mandatory)][string]$Label
    )

    $packageJsonPath = Join-Path $RepoPath "package.json"
    if (-not (Test-Path $packageJsonPath)) {
        return ""
    }

    $currentVersion = Get-PackageJsonVersion -PackageJsonPath $packageJsonPath
    if ([string]::IsNullOrWhiteSpace($currentVersion)) {
        throw "Could not read version from $packageJsonPath"
    }

    $nextVersion = Get-NextPatchVersion -VersionString $currentVersion
    Set-PackageJsonVersion -PackageJsonPath $packageJsonPath -VersionString $nextVersion
    Write-Host "  [OK]  $Label version bumped $currentVersion --> $nextVersion" -ForegroundColor Green
    return $nextVersion
}

function Confirm-VscePublishedVersion {
    param(
        [Parameter(Mandatory)][string]$ExtensionId,
        [Parameter(Mandatory)][string]$ExpectedVersion
    )

    $output = npx @vscode/vsce show $ExtensionId 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($output | Out-String))) {
        Write-Host "  [WARN]  Could not verify marketplace version for $ExtensionId" -ForegroundColor Yellow
        return $false
    }

    $joined = ($output | Out-String)
    $match = [regex]::Match($joined, 'Version:\s*([^\r\n]+)')
    if (-not $match.Success) {
        Write-Host "  [WARN]  Marketplace version for $ExtensionId could not be parsed" -ForegroundColor Yellow
        return $false
    }

    $publishedVersion = $match.Groups[1].Value.Trim()
    if ($publishedVersion -eq $ExpectedVersion) {
        Write-Host "  [OK]  Marketplace version verified: $ExtensionId v$publishedVersion" -ForegroundColor Green
        return $true
    }

    Write-Host "  [WARN]  Marketplace still shows $ExtensionId v$publishedVersion (expected v$ExpectedVersion). This is usually propagation delay." -ForegroundColor Yellow
    return $false
}

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

    # Pre-sync hygiene: drop generated caches in pool + target project .github
    Remove-JunaiCacheDirs -RootPath $JUNO_GITHUB -Label "pool"
    Remove-JunaiCacheDirs -RootPath $target -Label "project"

    foreach ($folder in $POOL_FOLDERS) {
        $src = Join-Path $JUNO_GITHUB $folder
        $dest = Join-Path $target $folder
        if (Test-Path $src) {
            # Clean destination first to avoid folder nesting and stale files.
            if (Test-Path $dest) {
                Remove-Item $dest -Recurse -Force
            }
            Copy-Item $src $target -Recurse -Force
            Write-Host "  [OK]  $folder" -ForegroundColor Green
        } else {
            # If a folder no longer exists in pool, remove stale copy locally.
            if (Test-Path $dest) {
                Remove-Item $dest -Recurse -Force
                Write-Host "  [OK]  $folder - removed stale local folder" -ForegroundColor Green
            } else {
                Write-Host "  [--]  $folder - not found in pool, skipped" -ForegroundColor Yellow
            }
        }
    }

    foreach ($file in $POOL_FILES) {
        $src = Join-Path $JUNO_GITHUB $file
        $dest = Join-Path $target $file
        if (Test-Path $src) {
            Copy-Item $src $dest -Force
            Write-Host "  [OK]  $file" -ForegroundColor Green
        } else {
            Write-Host "  [--]  $file - not found in pool, skipped" -ForegroundColor Yellow
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
        [string]$Message = "",
        [switch]$Publish,
        [switch]$NoPublish,
        [string]$McpVersion = ""
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

    # Pre-sync hygiene: remove generated caches on both sides so they never leak
    # into the public mirror or get reintroduced by additive copies.
    Remove-JunaiCacheDirs -RootPath $source -Label "source"
    Remove-JunaiCacheDirs -RootPath $JUNO_GITHUB -Label "mirror"

    foreach ($folder in $POOL_FOLDERS) {
        $src = Join-Path $source $folder
        $dest = Join-Path $JUNO_GITHUB $folder
        if (Test-Path $src) {
            # Clean destination first to prevent nested folder copies (e.g. diagrams/diagrams)
            # and to ensure moved/deleted files are mirrored correctly.
            if (Test-Path $dest) {
                Remove-Item $dest -Recurse -Force
            }
            Copy-Item $src $JUNO_GITHUB -Recurse -Force
            Write-Host "  [OK]  $folder" -ForegroundColor Green
        } else {
            # Source no longer has this folder: remove stale mirror copy.
            if (Test-Path $dest) {
                Remove-Item $dest -Recurse -Force
                Write-Host "  [OK]  $folder - removed stale mirror folder" -ForegroundColor Green
            } else {
                Write-Host "  [--]  $folder - not in project, skipped" -ForegroundColor DarkGray
            }
        }
    }

    foreach ($file in $POOL_FILES) {
        $src = Join-Path $source $file
        $dest = Join-Path $JUNO_GITHUB $file
        if (Test-Path $src) {
            Copy-Item $src $dest -Force
            Write-Host "  [OK]  $file" -ForegroundColor Green
        } else {
            Write-Host "  [--]  $file - not in project, skipped" -ForegroundColor DarkGray
        }
    }

    foreach ($file in $ROOT_PUSH_FILES) {
        $src = Join-Path $ProjectRoot $file
        $dest = Join-Path $JUNO_POOL $file
        if (Test-Path $src) {
            Copy-Item $src $dest -Force
            Write-Host "  [OK]  $file" -ForegroundColor Green
        } else {
            Write-Host "  [--]  $file - not in project root, skipped" -ForegroundColor DarkGray
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

    # Stage all tracked/untracked/deleted files in junai so source deletions and
    # folder moves are guaranteed to propagate.
    git add -A | Out-Null

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

    # Build profile exports used by downstream Ptarmigan/Liffey sync lanes.
    Push-Location $ProjectRoot
    python export_runtime_resources.py --profile ptarmigan --profile liffey --report
    $profileExportOk = ($LASTEXITCODE -eq 0)
    if ($profileExportOk -and (Test-Path (Join-Path $ProjectRoot "validate_pool.py"))) {
        python validate_pool.py --include-dist
        $profileExportOk = ($LASTEXITCODE -eq 0)
    }
    Pop-Location

    if (-not $profileExportOk) {
        Write-Host "  [WARN]  Profile export failed; skipping Ptarmigan/Liffey cascade for this run." -ForegroundColor Yellow
    } else {
        sync-ptarmigan -ProjectRoot $ProjectRoot -Message $Message -NoPublish:$NoPublish
        sync-liffey -ProjectRoot $ProjectRoot -Message $Message
    }

    # ── Auto-publish when key files exist ─────────────────────────────────
    $pypiToken = Get-JunaiSecretValue -EnvName "JUNAI_PYPI_TOKEN" -LegacyFilePath $PYPI_KEY_FILE
    $vscePat = Get-JunaiSecretValue -EnvName "JUNAI_VSCE_PAT" -LegacyFilePath $VSCE_PAT_FILE
    $hasPypiKey = -not [string]::IsNullOrWhiteSpace($pypiToken)
    $hasVscePat = -not [string]::IsNullOrWhiteSpace($vscePat)
    $hasAnyKey = $hasPypiKey -or $hasVscePat
    $shouldPublish = $Publish -or (-not $NoPublish -and $hasAnyKey)

    if ($NoPublish) {
        Write-Host "  [--]  Publish skipped (-NoPublish)." -ForegroundColor DarkGray
        return
    }

    if (-not $shouldPublish) {
        Write-Host "  [--]  No publish keys found. Skipping release." -ForegroundColor DarkGray
        Write-Host "       Set JUNAI_PYPI_TOKEN and/or JUNAI_VSCE_PAT in $JUNAI_ENV_FILE (legacy key files still work)." -ForegroundColor DarkGray
        return
    }

    if (-not $hasPypiKey) {
        Write-Host "  [--]  PyPI key missing; MCP publish skipped." -ForegroundColor DarkGray
    }
    if (-not $hasVscePat) {
        Write-Host "  [--]  VS Code PAT missing; extension publish skipped." -ForegroundColor DarkGray
    }

    junai-release -McpVersion $McpVersion -SkipMcp:(-not $hasPypiKey) -SkipExtension:(-not $hasVscePat)
}

function Sync-JunaiProfileRepo {
    param(
        [Parameter(Mandatory)][string]$Profile,
        [Parameter(Mandatory)][string]$ProjectRoot,
        [Parameter(Mandatory)][string]$RepoPath,
        [string]$Message = "",
        [switch]$NoPush
    )

    $exportRoot = Join-Path $ProjectRoot "dist\runtime-resources\$Profile"
    $sourceGithub = Join-Path $exportRoot ".github"
    $targetGithub = Join-Path $RepoPath ".github"

    if (-not (Test-Path $sourceGithub)) {
        Write-Host "  [WARN]  $Profile export not found at $sourceGithub" -ForegroundColor Yellow
        return $false
    }
    if (-not (Test-Path $RepoPath)) {
        Write-Host "  [WARN]  $Profile repo not found at $RepoPath" -ForegroundColor Yellow
        return $false
    }

    if (Test-Path $targetGithub) {
        Remove-Item $targetGithub -Recurse -Force
    }
    Copy-Item $sourceGithub $RepoPath -Recurse -Force

    Push-Location $RepoPath
    git add -A | Out-Null
    $hasChanges = (git status --porcelain) -ne $null
    if (-not $hasChanges) {
        Write-Host "  [--]  $Profile repo already up to date" -ForegroundColor DarkGray
        Pop-Location
        return $false
    }

    if ([string]::IsNullOrWhiteSpace($Message)) {
        $today = Get-Date -Format "yyyy-MM-dd"
        $Message = "feat: sync $Profile profile from agent-sandbox - $today"
    }

    git commit -m $Message | Out-Null
    if ($NoPush) {
        Write-Host "  [OK]  $Profile committed locally (no push)" -ForegroundColor Green
        Pop-Location
        return $true
    }

    git push | Out-Null
    Write-Host "  [OK]  $Profile committed + pushed" -ForegroundColor Green
    Pop-Location
    return $true
}

function Sync-ExtensionRepo {
    # Shared helper for ptarmigan and liffey.
    # Runs bundle-pool.js in the repo (populates pool/ from the junai mirror),
    # then copies the pre-built out/extension.js from junai-vscode, commits, and
    # optionally pushes.  Returns $true if a commit was made, $false otherwise.
    param(
        [Parameter(Mandatory)][string]$RepoPath,
        [Parameter(Mandatory)][string]$Label,
        [string]$ProjectRoot = "",
        [string]$Message = "",
        [switch]$NoPush,
        [switch]$AutoBumpVersion
    )

    if (-not (Test-Path $RepoPath)) {
        Write-Host "  [WARN]  $Label repo not found at $RepoPath" -ForegroundColor Yellow
        return $false
    }

    # 1. Refresh pool/ via the repo's own bundle-pool.js
    Push-Location $RepoPath
    $prevJunaiSource = $env:JUNAI_SOURCE
    try {
        if (-not [string]::IsNullOrWhiteSpace($ProjectRoot)) {
            $env:JUNAI_SOURCE = $ProjectRoot
        }
        node scripts/bundle-pool.js | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [WARN]  $Label bundle-pool failed." -ForegroundColor Yellow
            Pop-Location
            return $false
        }
    } finally {
        $env:JUNAI_SOURCE = $prevJunaiSource
    }

    # 2. Refresh out/ from the canonical junai-vscode build
    $outSrc = Join-Path $JUNAI_VSCODE "out"
    if (Test-Path $outSrc) {
        Copy-Item $outSrc $RepoPath -Recurse -Force
    }

    # 3. Commit if anything changed
    $hasChanges = (git status --porcelain) -ne $null
    if (-not $hasChanges) {
        Write-Host "  [--]  $Label repo already up to date" -ForegroundColor DarkGray
        Pop-Location
        return $false
    }

    if ($AutoBumpVersion) {
        $null = Bump-PackageJsonPatchVersion -RepoPath $RepoPath -Label $Label

        $prevJunaiSource = $env:JUNAI_SOURCE
        try {
            if (-not [string]::IsNullOrWhiteSpace($ProjectRoot)) {
                $env:JUNAI_SOURCE = $ProjectRoot
            }
            node scripts/bundle-pool.js | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  [WARN]  $Label bundle-pool refresh after version bump failed." -ForegroundColor Yellow
                Pop-Location
                return $false
            }
        } finally {
            $env:JUNAI_SOURCE = $prevJunaiSource
        }
    }

    git add -A | Out-Null

    if ([string]::IsNullOrWhiteSpace($Message)) {
        $today = Get-Date -Format "yyyy-MM-dd"
        $Message = "feat: sync $($Label.ToLower()) pool from agent-sandbox - $today"
    }
    git commit -m $Message | Out-Null

    if ($NoPush) {
        Write-Host "  [OK]  $Label committed locally (no push)" -ForegroundColor Green
        Pop-Location
        return $true
    }

    git push | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [WARN]  $Label push failed." -ForegroundColor Yellow
        Pop-Location
        return $true  # committed, push failed — caller can retry
    }

    Write-Host "  [OK]  $Label committed + pushed" -ForegroundColor Green
    Pop-Location
    return $true
}

function sync-ptarmigan {
    param(
        [string]$ProjectRoot = $PSScriptRoot,
        [string]$Message = "",
        [switch]$NoPush,
        [switch]$NoPublish
    )

    Write-Host "  PTARMIGAN SYNC  junai mirror --> $PTARMIGAN_REPO (pool/)" -ForegroundColor Cyan
    $changed = Sync-ExtensionRepo -RepoPath $PTARMIGAN_REPO -Label "Ptarmigan" -ProjectRoot $ProjectRoot -Message $Message -NoPush:$NoPush -AutoBumpVersion
    if (-not $changed -or $NoPush -or $NoPublish) {
        return
    }

    Push-Location $PTARMIGAN_REPO
    $pat = Get-JunaiSecretValue -EnvName "PTARMIGAN_VSCE_PAT" -LegacyFilePath $PTARMIGAN_PAT_FILE
    if ([string]::IsNullOrWhiteSpace($pat)) {
        Write-Host "  [--]  Ptarmigan PAT missing; publish skipped." -ForegroundColor DarkGray
        Pop-Location
        return
    }

    $prevVscePat = $env:VSCE_PAT
    try {
        $env:VSCE_PAT = $pat
        npx vsce publish --pat $pat --no-dependencies
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [WARN]  Ptarmigan publish failed." -ForegroundColor Yellow
        } else {
            Write-Host "  [OK]  Ptarmigan extension published." -ForegroundColor Green
            $expectedVersion = Get-PackageJsonVersion -PackageJsonPath (Join-Path $PTARMIGAN_REPO "package.json")
            if (-not [string]::IsNullOrWhiteSpace($expectedVersion)) {
                Confirm-VscePublishedVersion -ExtensionId "junai-labs.ptarmigan" -ExpectedVersion $expectedVersion | Out-Null
            }
        }
    } finally {
        $env:VSCE_PAT = $prevVscePat
        Pop-Location
    }
}

function sync-liffey {
    param(
        [string]$ProjectRoot = $PSScriptRoot,
        [string]$Message = "",
        [switch]$NoPush
    )

    Write-Host "  LIFFEY SYNC   junai mirror --> $LIFFEY_REPO (pool/)" -ForegroundColor Cyan
    $changed = Sync-ExtensionRepo -RepoPath $LIFFEY_REPO -Label "Liffey" -ProjectRoot $ProjectRoot -Message $Message -NoPush:$NoPush -AutoBumpVersion
    if (-not $changed) {
        return
    }

    Push-Location $LIFFEY_REPO
    $pkg = Get-Content (Join-Path $LIFFEY_REPO "package.json") -Raw | ConvertFrom-Json
    $version = if ($pkg.version) { $pkg.version } else { "0.0.0" }

    $distDir = Join-Path $LIFFEY_REPO "dist"
    New-Item -ItemType Directory -Path $distDir -Force | Out-Null

    $vsixOut = Join-Path $distDir "liffey-$version.vsix"
    npx vsce package --out $vsixOut --no-dependencies
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [WARN]  Liffey VSIX packaging failed." -ForegroundColor Yellow
    } else {
        Write-Host "  [OK]  Liffey VSIX prepared: $vsixOut" -ForegroundColor Green
    }
    Pop-Location
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

function junai-release {
    # Publishes MCP package and VS Code extension using .env secrets first,
    # with legacy key files as fallback.
    #
    # Usage:
    #   junai-release                        # publish both MCP + extension
    #   junai-release -SkipMcp               # extension only
    #   junai-release -SkipExtension         # MCP only
    #   junai-release -McpVersion "0.2.2"    # bump MCP version before publish
    #   junai-release -ExtensionVersion "1.2.3"
    param(
        [string]$McpVersion = "",
        [string]$ExtensionVersion = "",
        [switch]$SkipMcp,
        [switch]$SkipExtension
    )

    Write-Host ""
    Write-Host "  JUNAI RELEASE  MCP + VS Code" -ForegroundColor Cyan
    Write-Host "  -----------------------------------------" -ForegroundColor DarkGray

    # -- Pre-publish agent validation gate --
    $validatorScript = Join-Path $REPO_ROOT "validate_agents.py"
    $poolValidatorScript = Join-Path $REPO_ROOT "validate_pool.py"
    $pythonExe       = Join-Path $REPO_ROOT ".venv\Scripts\python.exe"
    if ((Test-Path $validatorScript) -and (Test-Path $pythonExe)) {
        & $pythonExe $validatorScript
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  [ABORT]  Agent validation failed. Fix errors above before publishing." -ForegroundColor Red
            return
        }

        if (Test-Path $poolValidatorScript) {
            & $pythonExe $poolValidatorScript
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  [ABORT]  Pool validation failed. Fix errors above before publishing." -ForegroundColor Red
                return
            }
        }
    } else {
        Write-Host "  [WARN]  validate_agents.py/validate_pool.py or venv not found -- skipping validation" -ForegroundColor Yellow
    }

    if (-not $SkipMcp) {
        $pypiToken = Get-JunaiSecretValue -EnvName "JUNAI_PYPI_TOKEN" -LegacyFilePath $PYPI_KEY_FILE
        if ([string]::IsNullOrWhiteSpace($pypiToken)) {
            Write-Host "  [ERROR] Missing PyPI token. Set JUNAI_PYPI_TOKEN in $JUNAI_ENV_FILE or keep $PYPI_KEY_FILE." -ForegroundColor Red
            return
        }

        $prevTwineUser = $env:TWINE_USERNAME
        $prevTwinePass = $env:TWINE_PASSWORD
        try {
            $env:TWINE_USERNAME = "__token__"
            $env:TWINE_PASSWORD = $pypiToken
            junai-publish-mcp -Version $McpVersion
        } finally {
            $env:TWINE_USERNAME = $prevTwineUser
            $env:TWINE_PASSWORD = $prevTwinePass
        }
    }

    if (-not $SkipExtension) {
        $vscePat = Get-JunaiSecretValue -EnvName "JUNAI_VSCE_PAT" -LegacyFilePath $VSCE_PAT_FILE
        if ([string]::IsNullOrWhiteSpace($vscePat)) {
            Write-Host "  [ERROR] Missing VS Code PAT. Set JUNAI_VSCE_PAT in $JUNAI_ENV_FILE or keep $VSCE_PAT_FILE." -ForegroundColor Red
            return
        }

        if (-not (Test-Path (Join-Path $JUNAI_VSCODE "package.json"))) {
            Write-Host "  [ERROR] junai-vscode repo not found at $JUNAI_VSCODE" -ForegroundColor Red
            return
        }

        $prevVscePat = $env:VSCE_PAT
        try {
            $env:VSCE_PAT = $vscePat
            Push-Location $JUNAI_VSCODE
            $packageJsonPath = Join-Path $JUNAI_VSCODE "package.json"
            $currentExtensionVersion = Get-PackageJsonVersion -PackageJsonPath $packageJsonPath
            if ([string]::IsNullOrWhiteSpace($currentExtensionVersion)) {
                Write-Host "  [ERROR] Could not read junai-vscode package version." -ForegroundColor Red
                return
            }

            if ([string]::IsNullOrWhiteSpace($ExtensionVersion)) {
                $ExtensionVersion = Get-NextPatchVersion -VersionString $currentExtensionVersion
            }

            if ($ExtensionVersion -ne $currentExtensionVersion) {
                Set-PackageJsonVersion -PackageJsonPath $packageJsonPath -VersionString $ExtensionVersion
                git add package.json
                git commit -m "chore: bump version to $ExtensionVersion" | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  [ERROR] junai-vscode version bump commit failed." -ForegroundColor Red
                    return
                }
                git push | Out-Null
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "  [ERROR] junai-vscode version bump push failed." -ForegroundColor Red
                    return
                }
                Write-Host "  [OK]  junai-vscode version bumped $currentExtensionVersion --> $ExtensionVersion" -ForegroundColor Green
            } else {
                Write-Host "  [--]  junai-vscode version unchanged at $currentExtensionVersion" -ForegroundColor DarkGray
            }

            Write-Host "  Publishing VS Code extension..." -ForegroundColor DarkGray
            npx vsce publish --pat $vscePat --no-dependencies
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  [ERROR] VS Code extension publish failed." -ForegroundColor Red
                return
            }

            Confirm-VscePublishedVersion -ExtensionId "junai-labs.junai" -ExpectedVersion $ExtensionVersion | Out-Null
        } finally {
            Pop-Location
            $env:VSCE_PAT = $prevVscePat
        }
    }

    Write-Host "  [OK]  Release flow completed." -ForegroundColor Green
    Write-Host ""
}

function junai-revert {
    # Reverts one or more commits in agent-sandbox and cascades to all downstream
    # repos (junai, junai-vscode, and any explicit project repos).
    # Safe -- new revert commits, no history rewrite.
    #
    # Usage:
    #   junai-revert                                         # revert HEAD (last commit)
    #   junai-revert -Last 3                                 # revert last 3 commits
    #   junai-revert -Sha abc123                             # revert one specific commit
    #   junai-revert -Sha abc123,def456,ghi789               # revert multiple commits
    #   junai-revert -Last 2 -NoCascade                      # revert agent-sandbox only
    #   junai-revert -Last 3 -Force                          # skip confirmation (chat / CI use)
    #   junai-revert -Last 3 -Projects "E:\Projects\Foo"     # also restore pool in project repo
    #   junai-revert -Last 3 -Projects "E:\P\Foo,E:\P\Bar"  # multiple project repos
    param(
        [string[]]$Sha       = @(),
        [int]$Last           = 0,
        [string]$Message     = "",
        [string[]]$Projects  = @(),
        [switch]$NoCascade,
        [switch]$Force
    )

    $agentSandbox = $REPO_ROOT

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
    $allHashes = @(git log --format="%H")
    $resolved  = $allHashes | Where-Object { $resolved -contains $_ }

    # Expand comma-separated project paths
    $projectList = $Projects | ForEach-Object { $_ -split ',' } |
                               ForEach-Object { $_.Trim() } |
                               Where-Object   { $_ -ne '' }

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
        foreach ($proj in $projectList) {
            Write-Host "              --> $(Split-Path $proj -Leaf)  (junai-pull + commit)" -ForegroundColor DarkGray
        }
    }
    Write-Host ""

    if (-not $Force) {
        $confirm = Read-Host "  Proceed? (y/N)"
        if ($confirm -notmatch '^[Yy]$') {
            Write-Host "  Cancelled." -ForegroundColor DarkGray
            Pop-Location; return
        }
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
        $srcSync = Join-Path $agentSandbox "sync.ps1"
        $dstSync = Join-Path $JUNO_POOL    "sync.ps1"
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

        # 4. Project repos -- restore reverted pool via junai-pull + commit + push
        foreach ($proj in $projectList) {
            $githubDir = Join-Path $proj ".github"
            if (-not (Test-Path $githubDir)) {
                Write-Host "  [SKIP] $(Split-Path $proj -Leaf) -- no .github/ found" -ForegroundColor Yellow
                continue
            }
            Write-Host "  Restoring pool in $(Split-Path $proj -Leaf) ..." -ForegroundColor DarkGray
            junai-pull -ProjectRoot $proj
            Push-Location $proj
            $dirty = (git status --porcelain) -ne $null
            if ($dirty) {
                git add ".github"
                git commit -m "$revertMsg (pool)" | Out-Null
                git push | Out-Null
                Write-Host "  [OK]  $(Split-Path $proj -Leaf) pool reverted and pushed" -ForegroundColor Green
            } else {
                Write-Host "  [--]  $(Split-Path $proj -Leaf) -- pool already up to date" -ForegroundColor DarkGray
            }
            Pop-Location
        }
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

    # Pre-export hygiene: remove generated caches from source + export target.
    Remove-JunaiCacheDirs -RootPath $JUNO_GITHUB -Label "pool"
    Remove-JunaiCacheDirs -RootPath $OutputPath -Label "export"

    foreach ($folder in $POOL_FOLDERS) {
        $src = Join-Path $JUNO_GITHUB $folder
        $dest = Join-Path $OutputPath $folder
        if (Test-Path $src) {
            if (Test-Path $dest) {
                Remove-Item $dest -Recurse -Force
            }
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

    # Pre-import hygiene: remove generated caches in import source + target.
    Remove-JunaiCacheDirs -RootPath $SourcePath -Label "import source"
    Remove-JunaiCacheDirs -RootPath $target -Label "project"

    foreach ($folder in $POOL_FOLDERS) {
        $src = Join-Path $SourcePath $folder
        $dest = Join-Path $target $folder
        if (Test-Path $src) {
            # Clean destination first to prevent folder nesting and stale files.
            if (Test-Path $dest) {
                Remove-Item $dest -Recurse -Force
            }
            Copy-Item $src $target -Recurse -Force
            Write-Host "  [OK]  $folder" -ForegroundColor Green
        } else {
            # Import source no longer has this folder: remove stale local copy.
            if (Test-Path $dest) {
                Remove-Item $dest -Recurse -Force
                Write-Host "  [OK]  $folder - removed stale local folder" -ForegroundColor Green
            } else {
                Write-Host "  [--]  $folder - not in export, skipped" -ForegroundColor Yellow
            }
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
