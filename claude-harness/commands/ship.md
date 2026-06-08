---
description: Commit, push, and monitor the Gitea CalVer/NSSM deploy pipeline to prod
argument-hint: "[commit message]"
---

# /ship — commit → push → CI → prod

Ship the current working changes to prod via the Gitea CalVer/NSSM pipeline.

Optional message: **$ARGUMENTS** (if empty, derive a conventional commit message from staged changes)

Read `CLAUDE.md` and `.gitea/workflows/ci.yml` before starting so you know the actual gate names
and NSSM service identifiers for this repo. Follow the `deploy-local` skill workflow exactly.

## Steps — do not skip or reorder

**1. PREFLIGHT** — Run local quality gates that mirror CI:
- Backend: `ruff check .` (must be clean before any commit)
- Frontend: `npm run typecheck && npm run build` (if frontend/ exists)
- Tests: run only if the user says they're needed or a gate explicitly requires them
- Fix any failures before proceeding. Do not commit broken code.

**2. STAGE + COMMIT** — Stage only the intended files (never `git add -A` blindly):
```
git status --short      # confirm what's staged
git add <specific files>
git commit -m "<type>(<scope>): <message>"
git rev-parse HEAD      # record SHA for monitoring
```
Use conventional commits: `fix:`, `feat:`, `chore:`, `refactor:`, `docs:`. Scope = affected module.

**3. PUSH**
```
git push origin main
```
Confirm the push succeeded and the SHA is accepted by the remote.

**4. MONITOR CI** — Poll the Gitea API using the token from `config/.env.gitea` (load it first):
```powershell
$envFile = Join-Path (Get-Location) "config/.env.gitea"
# ... (load VMIE_BOT_TOKEN from file — see deploy-local skill)
```
Track jobs in order: `lint_and_test` → `frontend_checks` (if present) → `deploy_prod` →
`release_metadata` → `notify`. Report status as each job completes. If any job fails, classify
the failure and apply the minimum fix (see deploy-local skill §6).

**5. PROD VALIDATION** — After `deploy_prod` succeeds:
- Prod checkout SHA matches the pushed commit
- NSSM services for this repo are Running
- Health endpoint returns green
- Version endpoint shows the expected SHA/CalVer (if the repo exposes one)

**6. REPORT** — Emit the deploy report:
```
Repo:            <name>
Commit:          <sha> — <message>
CI jobs:         lint_and_test ✓  deploy_prod ✓  release_metadata ✓
Prod SHA:        matches ✓
Prod health:     green ✓
CalVer tag:      v<tag> → <sha>
```

## Rules
- Never push before preflight gates are green.
- Never use `git add -A` without reviewing `git status` first.
- Do not change `.gitea/workflows/` to make a failing gate pass — fix the source.
- Tag-triggered runs after `release_metadata` are expected; verify `deploy_prod` is **skipped** in them.
- If prod health is red after deploy, report it immediately — do not attempt a silent re-deploy.

## Skill reference
Full procedures for CI monitoring, prod validation, queue triage, and failure remediation are in
`skills/devops/deploy-local/SKILL.md`. Load it when any step needs more detail.
