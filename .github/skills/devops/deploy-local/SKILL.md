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
