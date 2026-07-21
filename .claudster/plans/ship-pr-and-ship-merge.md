---
type: plan
status: in-progress
feature: ship-pr-and-ship-merge
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-20T00:00:00Z
Creating Model: claude-opus-4-8
---

# `/ship-pr` and `/ship-merge` — the reviewed lane for claudster

## Why

`/ship` today is the **express lane**: preflight → commit → push → watch deploy. On a repo where a
push to the default branch deploys (the VMIE Gitea/NSSM setup), running `/ship` on `main` sends work
straight to prod with **no review pause**. That is correct for a hotfix, wrong for feature work.

The missing half is the **reviewed lane**: land feature-branch work on `main` *through a Pull
Request*, so CI + a human gate run **before** the deploy, not after. Right now that flow is manual
(`gh` / Gitea PR creation, merge, branch cleanup) and re-learned each time.

Two commands close the gap, split at the one place a human must stay in the loop:

- **`/ship-pr`** — mechanics only, fully automatable: rebase-safe push → open PR → monitor PR CI →
  **stop at green** and report mergeability. Never merges, never deploys.
- **`/ship-merge`** — the deliberate second door: merge an *already-green, already-reviewed* PR →
  monitor the deploy → post-deploy validation → **branch cleanup**. Human-gated, because on these
  repos **merge == deploy**.

### The anti-pattern we are explicitly NOT building
A single `/ship-merge` that *creates and merges in one shot*. That recreates the exact problem PRs
exist to prevent: the ceremony of review with none of the pause. The split above is the whole point —
`/ship-pr` produces a reviewable artifact and stops; the merge stays a separate, intentional act.

## Portability constraint (this ships in the plugin)

These commands live in the pool and reach every app the user opens. They **must** reuse `/ship`'s
lane-detection model and hardcode nothing app-specific:

- **Gitea lane** — `.gitea/workflows/` present. PR + merge via the Gitea API; CI/deploy monitoring
  via the existing `.github/skills/devops/deploy-local/SKILL.md`.
- **GitHub lane** — `.github/workflows/` present (no `.gitea/`). PR + merge + monitoring via `gh`
  (`.github/skills/devops/gh-cli/SKILL.md`).
- **Local-only lane** — neither, or no remote. There is no PR concept: **refuse early**, tell the
  user to use `/ship`, and stop. Do not fabricate a PR flow.

Read `CLAUDE.md` + the detected workflow file(s) at runtime for the repo's real gate names, default
branch, and service identifiers — never assume `main`, never assume job names.

## Current state (verified 2026-07-20)

- Command source of truth: `claude-harness/commands/*.md` (authoritative; `dist/runtime-resources/…`
  and `vscode-extensions/junai/plugin/…` are **generated** by `export_runtime_resources.py` — never
  hand-edit those).
- `claude-harness/commands/ship.md` exists and already encodes the three-lane detection + preflight +
  monitor + validate structure. **`/ship-pr` and `/ship-merge` mirror its frontmatter and lane model.**
- Skills to reuse (present): `.github/skills/devops/deploy-local/SKILL.md` (Gitea CI/prod monitor),
  `.github/skills/devops/gh-cli/SKILL.md` (`gh run` / `gh pr`).
- Command test harness: `scripts/tests/` (e.g. `test_implement_command.py`, `test_headless_convention.py`,
  `test_export_runtime_resources.py`). New commands get a matching source-scanning test here.
- Quality gates: `validate_pool.py` (+ `--profile claude` / `--profile claude-extras`),
  `python -m pytest scripts/tests`.
- Build/publish: `export_runtime_resources.py` → `dist/`; `junai-push` (mirror sync + plugin version
  bump, **no publish**). Publishing is a separate opt-in (`-Publish`) and is out of scope for this plan.

## Design contracts (cite these from every phase)

### C1 — `/ship-pr` steps (Gitea/GitHub lanes)
1. **Detect lane** (§ above). Local-only → refuse + stop.
2. **Refuse on the default branch.** A PR is branch→main; if HEAD *is* the default branch, stop and
   point at `/ship`.
3. **Preflight** — run the repo's local gates mirroring CI (`ruff check`, `npm run build`/typecheck if
   `frontend/`). Never open a PR over red preflight.
4. **Scope-guard pre-check** — if the repo has a scope-guard workflow (e.g. Gitea `pr-scope-guard`
   blocking PRs that mix infra `.gitea/`,`.github/` with product `src/`,`frontend/`,`tests/`), detect a
   mixed diff **before** creating the PR and refuse early with the specific offending files. Do not let
   the guard fail the PR after the fact.
5. **Rebase-safe currency** — offer to rebase the branch onto latest default branch (stale branches are
   how merges rot). If the branch is already pushed, a rebase rewrites history → **snapshot a
   `backup/<branch>-preship` ref first**, then `push --force-with-lease`. (This is the exact safety the
   2026-07 rev-sight voice/SMS push needed — encode it, don't rediscover it.)
6. **Push** the branch.
7. **Create the PR** (title from the branch's conventional-commit summary; body = commit list + a
   "generated by /ship-pr" note). Idempotent: if a PR for this branch already exists, update/report it
   rather than erroring.
8. **Monitor PR CI** job-by-job (never the deploy — PRs don't deploy here) + the scope-guard check.
9. **Stop at green.** Report: PR URL, per-check status, and a one-line **mergeable? yes / blocked-by-X**.
   Never merge.

### C2 — `/ship-merge` steps
1. **Detect lane**; resolve the target PR (arg `$ARGUMENTS` = PR number/URL, else infer from the
   current branch's open PR).
2. **Refuse unless the PR is green + mergeable + reviewed** per the repo's rules (required checks
   passed, scope-guard passed, no merge conflicts). Report exactly what's missing and stop.
3. **Explicit human-confirm gate** — state plainly "merging this PR will DEPLOY <sha> to prod via the
   pipeline" and require confirmation. This is the one irreversible, outward-facing step; approval here
   does not carry over to a future run.
4. **Merge** the PR (repo's default merge strategy; confirm which — squash vs merge-commit — from repo
   settings/CLAUDE.md, don't assume).
5. **Monitor the deploy** on the default branch via the lane's skill (`deploy-local` / `gh-cli`):
   `deploy_prod` (or the GitHub deploy job) → release metadata → notify.
6. **Post-deploy validation** — prod/target SHA matches the merge commit; services Running; health
   green; version endpoint shows the expected SHA/CalVer (reuse `/ship` Step 5).
7. **Branch cleanup (only after a confirmed-green deploy)** — delete the remote feature branch, delete
   the local feature branch, switch back to the default branch and fast-forward it, and drop the
   `backup/<branch>-preship` ref created by `/ship-pr`. If deploy validation failed, **skip cleanup**
   and report — never delete a branch whose work may need re-work.
8. **Report** (mirror `/ship` Step 6 + the cleanup outcome).

### C3 — Safety invariants (both commands)
- Never `git add -A` without reviewing `git status`.
- Never force-push without first writing a `backup/*` recovery ref.
- Never edit a workflow file to make a gate pass — fix the source.
- Never merge without: green required checks **and** explicit human confirm.
- Never delete a branch before its deploy is validated green.
- Local-only lane: no PR, no merge — degrade to a clear "use /ship" message.

## Phases

### Phase 0 — Contract doc (design lock)
**Goal:** turn C1–C3 into a short design section other phases cite; settle the merge-strategy and
scope-guard detection questions so no phase improvises.
**Touches:** this plan (fill any open question below), optionally a
`docs/analysis/reviewed-lane-contract.md` if the detail outgrows the plan.
**Exit gate:** C1–C3 unambiguous; open questions resolved or explicitly deferred.
**Commit:** `docs(plan): reviewed-lane (/ship-pr, /ship-merge) contract`

### Phase 1 — `/ship-pr` (RED → GREEN)
**RED:** add `scripts/tests/test_ship_pr_command.py` (mirror `test_implement_command.py` +
`test_headless_convention.py`): assert the command file exists, has valid frontmatter
(`description`, `argument-hint`), enumerates the three lanes, contains the scope-guard pre-check and the
`force-with-lease`+`backup/` safety wording, and **contains no merge/deploy step** (grep-assert absence
of a merge action). Run — it fails (no file).
**GREEN:** write `claude-harness/commands/ship-pr.md` implementing C1. Model frontmatter + lane prose on
`ship.md`. Reference the `deploy-local` / `gh-cli` skills for CI monitoring.
**REFACTOR:** factor any prose shared with `ship.md` into a cited skill rather than duplicating.
**Exit gate:** `pytest scripts/tests/test_ship_pr_command.py` green.
**Commit:** `feat(commands): /ship-pr — open a reviewed PR, monitor CI, stop at green`

### Phase 2 — `/ship-merge` (RED → GREEN)
**RED:** `scripts/tests/test_ship_merge_command.py`: assert the file exists, valid frontmatter, contains
the **explicit human-confirm/deploy-warning** gate, the **green-and-mergeable** precondition, the
post-deploy validation, and the **branch-cleanup-only-after-green** step; assert it refuses the
local-only lane. Run — fails.
**GREEN:** write `claude-harness/commands/ship-merge.md` implementing C2/C3.
**REFACTOR:** ensure cleanup + validation prose reuses `/ship` Step 5/6 by reference.
**Exit gate:** `pytest scripts/tests/test_ship_merge_command.py` green.
**Commit:** `feat(commands): /ship-merge — merge a green PR, watch deploy, clean up the branch`

### Phase 3 — Cross-references & discoverability
**Goal:** make the reviewed lane findable; stop `/ship` from being the only signpost.
**Touches:** `claude-harness/commands/ship.md` (add a "for feature work, use `/ship-pr` → `/ship-merge`"
pointer), any command index / CLAUDE.md fragment that lists commands, README if it enumerates commands.
**Exit gate:** `/ship`, `/ship-pr`, `/ship-merge` cross-link; no doc claims `/ship` is the only path to prod.
**Commit:** `docs(commands): cross-link express (/ship) and reviewed (/ship-pr,/ship-merge) lanes`

### Phase 4 — Build, validate, hand off publish
**Goal:** generated bundles + gates green; leave the (opt-in) publish to a human.
**Implement:** run `export_runtime_resources.py`; `validate_pool.py` (+ `--profile claude` /
`--profile claude-extras`); `python -m pytest scripts/tests`. Confirm the two new commands appear in
`dist/runtime-resources/claude/plugin/commands/` and the VS Code mirror.
**Exit gate:** validators + full test suite green; both commands present in the generated tree.
**Commit:** `chore(build): regenerate runtime resources for the reviewed-lane commands`
**HUMAN (out of scope):** `junai-push` (plugin version bump + mirror) and any `-Publish` — deliberately
not automated here (publish is irreversible/opt-in per README).

## Open questions — RESOLVED (Phase 0, 2026-07-21)
1. **Merge strategy** — **detect + allow override.** `/ship-merge` reads the repo's configured default
   (Gitea: repo settings via API; GitHub: `gh repo view --json squashMergeAllowed,mergeCommitAllowed,
   rebaseMergeAllowed,...` + `CLAUDE.md`); an explicit argument (`squash` | `merge` | `rebase`) wins.
   If detection is inconclusive, state the ambiguity and use merge-commit (never silently squash —
   squash rewrites history the branch's author may still hold).
2. **Scope-guard generality** — **two tiers.** A named guard workflow (e.g. Gitea `pr-scope-guard`) is
   authoritative: read the workflow's own rule and pre-check the diff against exactly that, refusing
   with the offending files. Without a named guard, the generic infra-vs-product mixed-diff heuristic
   (`.gitea/`,`.github/` mixed with `src/`,`frontend/`,`tests/`) is a **warning only** — surface it,
   don't refuse (repos without a guard allow mixed PRs by construction).
3. **Review requirement** — **the repo's rules decide.** When required reviewers/approvals are
   configured, `/ship-merge` refuses until they're satisfied. On a solo repo with none configured, the
   explicit human deploy-confirm in `/ship-merge` IS the review gate — sufficient, because the same
   human authored, reviewed the PR artifact, and confirms the deploy.
4. **Auto-rebase default** — **only when behind** the default branch, and only with consent; always
   write `backup/<branch>-preship` before any history rewrite; force-push only `--force-with-lease`.

## Tracker
| Phase | Status | Commit |
|---|---|---|
| 0 — Contract doc (design lock) | ✅ done | (this commit) |
| 1 — `/ship-pr` (RED → GREEN) | ⏳ pending | — |
| 2 — `/ship-merge` (RED → GREEN) | ⏳ pending | — |
| 3 — Cross-references & discoverability | ⏳ pending | — |
| 4 — Build, validate, hand off publish | ⏳ pending | — |

## Definition of done
- `/ship-pr` opens/updates a PR, monitors CI, stops at green, never merges/deploys — across Gitea +
  GitHub lanes; refuses the local-only lane and the default-branch case with clear messages.
- `/ship-merge` merges only a green+mergeable+reviewed PR behind an explicit deploy-confirm, validates
  the deploy, and cleans up the branch **only** on green.
- Both are pipeline-agnostic (no app-specific gate names), reuse `deploy-local`/`gh-cli`, and honor the
  C3 safety invariants.
- Tests in `scripts/tests` cover both; `validate_pool` + suite green; commands present in the generated
  bundles. Publish left to a human.
