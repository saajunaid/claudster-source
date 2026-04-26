---
name: deploy-local
description: End-to-end local deployment loop for VMIE Gitea projects. Use when the user wants to commit on dev, push to remote, monitor CI/build/deploy on prod, and automatically fix lint/test/pipeline failures until deployment is healthy.
---

# Deploy Local Skill

Run reliable local-to-prod delivery for VMIE repositories hosted on local Gitea.

## When To Use

Use this skill when requests include any of:
- "commit and deploy"
- "push and monitor pipeline"
- "watch prod deploy"
- "fix CI failures"
- "lint/test failing in pipeline"
- "stuck in queue"

## Required Companion Skills

Load these first:
- `.github/skills/devops/windows-deployment/SKILL.md`
- `.github/skills/devops/ci-cd-pipeline/SKILL.md`
- `.github/skills/devops/git-commit/SKILL.md`

Optional:
- `.github/skills/devops/gh-cli/SKILL.md` for issue/PR linking
- `.github/skills/workflow/verification-loop/SKILL.md` for stricter local validation loops

## VMIE Local Platform Defaults

- Gitea UI: `http://git.local:8090`
- Gitea API: `http://git.local:8090/api/v1`
- Expected non-prod runner label: `dev`
- Expected prod runner label: `prod`

## Phase 1: Preflight

1. Confirm repo root and current branch.
2. Run `git status --short`.
3. Run local quality gates that mirror CI:
   - Ruff lint/format or equivalent linter.
   - Test suite (or deploy-gate subset if repo policy defines one).
   - Frontend build where applicable.
4. If a gate fails, fix source code first.

## Phase 2: Commit + Push

1. Stage only intended files.
2. Commit with conventional message.
3. Push to target branch.
4. Capture commit SHA and remote ack.

Example commands:
```powershell
git add <files>
git commit -m "fix(ci): resolve lint failures in health router"
git push origin main
```

## Phase 3: CI and Deploy Monitoring

Monitor run lifecycle:
1. Trigger source: push or workflow_dispatch.
2. Track jobs in order:
   - lint/test gate
   - frontend checks
   - deploy
   - notify
3. If a gate fails:
   - classify failure as lint, format, test, build, workflow-runtime, infra-runner.
   - patch minimal fix.
   - re-run from commit/push.

## Phase 4: Prod Pull + Build + Deploy Validation

For Windows prod flow, validate:
1. Prod pull reached expected SHA.
2. Build completed with correct base path/asset references.
3. Deploy service restart succeeded.
4. Health endpoint returns success.
5. Optional: dev/prod SHA parity check.

Use windows-deployment skill patterns for NSSM and reverse proxy checks.

## Phase 4.5: CalVer Verification

Run after every successful deploy to confirm CalVer infrastructure delivered a valid version.
**Treat any FAIL as a deploy blocker — do not declare deployment complete until all checks pass.**

### V1 — Script existence

```powershell
$scripts = @(
    ".gitea\scripts\compute-version.ps1",
    ".gitea\scripts\generate-changelog.ps1",
    ".gitea\scripts\deploy.ps1"
)
foreach ($s in $scripts) {
    if (Test-Path $s) { Write-Host "[OK] $s" }
    else { Write-Warning "[FAIL] MISSING: $s — copy from platform-infra/templates/scripts/" }
}
```

### V2 — No non-ASCII in PowerShell scripts

> Unicode characters (e.g. em-dash `—`) cause silent runtime parse failures in PowerShell.

```powershell
foreach ($s in $scripts) {
    $hit = Select-String -Path $s -Pattern '[^\x00-\x7F]' -List
    if ($hit) { Write-Warning "[FAIL] NON-ASCII in $s : $($hit.Line)" }
    else       { Write-Host "[OK] $s — clean" }
}
```

**Fix**: Replace non-ASCII in string literals with `-f` format operator, e.g.:
```powershell
# BAD  (em-dash causes parse failure):  "## [$Version] — $date"
# GOOD (safe):                          ("## [{0}] - {1}" -f $Version, $date)
```

### V3 — PowerShell syntax parse gate

```powershell
foreach ($s in $scripts) {
    $err = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        (Resolve-Path $s).Path, [ref]$null, [ref]$err)
    if ($err.Count -gt 0) {
        Write-Warning "[FAIL] PARSE ERRORS in $s"
        $err | ForEach-Object { Write-Warning "  Line $($_.Extent.StartLineNumber): $($_.Message)" }
    } else {
        Write-Host "[OK] $s — parses clean"
    }
}
```

### V4 — `src/_version.json` written (backend artefact)

```powershell
if (Test-Path "src\_version.json") {
    $v = Get-Content "src\_version.json" | ConvertFrom-Json
    Write-Host "[OK] version=$($v.version)  environment=$($v.environment)"
} else {
    Write-Warning "[FAIL] src\_version.json missing — compute-version.ps1 did not run or failed"
}
```

### V5 — `frontend/dist/version.json` emitted (frontend artefact)

```powershell
if (Test-Path "frontend\dist\version.json") {
    Get-Content "frontend\dist\version.json" | ConvertFrom-Json | Select-Object version
    Write-Host "[OK] dist/version.json present"
} else {
    Write-Warning "[FAIL] frontend\dist\version.json missing — vite-version-plugin.ts may not be wired in vite.config.ts"
}
```

### V6 — `GET /api/version` returns valid CalVer string

```powershell
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:8201/api/version" -ErrorAction Stop
    if ($r.version -match '^v\d{4}\.\d{2}\.\d{2}\.\d+$' -or $r.version -match '^v\d{4}\.\d{2}') {
        Write-Host "[OK] /api/version → $($r.version) ($($r.environment))"
    } else {
        Write-Warning "[FAIL] Unexpected version format: $($r.version)"
    }
} catch {
    Write-Warning "[FAIL] GET /api/version failed: $($_.Exception.Message)"
    Write-Warning "       Check that version_router is registered in src/api/main.py"
}
```

### V7 — `src/_version.json` not tracked by git

```powershell
$s = git status --short src/_version.json
if (-not $s) { Write-Host "[OK] src/_version.json untracked (correct)" }
else { Write-Warning "[FAIL] src/_version.json appears in git status — add to .gitignore" }

# Confirm .gitignore entry:
Select-String "src/_version.json" .gitignore
```

### V8 — CHANGELOG.md populated after first tagged deploy

```powershell
if ((Test-Path "CHANGELOG.md") -and (Get-Content "CHANGELOG.md" -Raw).Trim()) {
    Write-Host "[OK] CHANGELOG.md has content"
    Get-Content "CHANGELOG.md" -TotalCount 5
} else {
    Write-Host "[INFO] CHANGELOG.md empty — will populate after first CalVer-tagged prod deploy"
}
```

### CalVer Failure Reference

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| `_version.json` missing | `compute-version.ps1` not run / missing | Copy from `platform-infra/templates/scripts/` |
| Version is `0.0.0` or blank | Script ran but no CalVer tag found | Ensure `tag_version` CI job pushed the tag before deploy |
| CHANGELOG not generated | `generate-changelog.ps1` parse failure (non-ASCII) | Run V2/V3 checks; replace em-dash |
| `GET /api/version` → 404 | `version_router` not in `main.py` | Add `app.include_router(version_router)` |
| `APP_VERSION` blank in frontend build | `tag_version` output not wired to `frontend_checks` env | Add `APP_VERSION: ${{ needs.tag_version.outputs.app_version }}` |
| `_version.json` in `git status` | Missing from `.gitignore` | Add `src/_version.json` under `# CalVer build artefact` |

## Phase 5: Queue / Runner Triage

If run is stuck waiting:
1. Verify workflow `runs-on` labels match available runners.
2. Check runner service health on host (NSSM service state).
3. Check workflow `concurrency` groups for blocking in-progress jobs.
4. Cancel stale runs if policy allows; rerun latest commit.

Do not change runner labels to temporary values unless explicitly approved.

## Phase 6: Failure Auto-Remediation Rules

### Lint/Format Failures
- Fix code directly and keep style-consistent.
- Re-run local lint before push.

### Test Failures
- Fix failing code/tests according to project policy.
- Keep behavior-preserving unless feature changes are requested.

### Workflow Runtime Failures
- Fix parser/shell/exit-code handling in workflow YAML.
- Ensure native command failures are fatal in PowerShell steps.

### Build/Deploy Failures
- Fix config or script with minimal blast radius.
- Validate with local command parity before push.

## Exit Criteria (Definition of Done)

All must be true:
1. Local lint/test/build checks pass.
2. Push succeeded and commit SHA recorded.
3. CI run completed with expected gates.
4. Deploy completed or intentionally skipped by gate logic.
5. Notify stage emitted correct success/failure signal.

## Report Template

```markdown
## Deploy Local Report
- Repo:
- Branch:
- Commit:
- CI Run:
- Gate Results:
  - lint/test:
  - frontend:
  - deploy:
  - notify:
- Fixes Applied:
- Final Status:
- Follow-ups (if any):
```

## Anti-Patterns

- Treating stale terminal output as current truth.
- Changing workflow orchestration before fixing clear source-code lint/test failures.
- Making quality gates non-blocking to force deployment.
- Declaring queue issues fixed without verifying runner availability and label alignment.
