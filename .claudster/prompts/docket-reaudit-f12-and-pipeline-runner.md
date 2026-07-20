# Driver — docket re-audit backlog (FULL) + F12 worktree isolation + pipeline-runner fix

You are the driver for the final three items of the Fable remediation queue, in this order:
**(1)** fix claudster's pipeline-runner, **(2)** implement EVERYTHING in the 2026-07-20 docket
re-audit, **(3)** docket F12 full worktree isolation. The user chose this scope explicitly
(2026-07-20): pipeline-runner = **fix, not retire**; audit scope = **everything, not just the top-10**.

## Orient first (read in this order — do NOT skip)
1. `.claudster/relay.md` — session state, validation baselines.
2. `docs/analysis/fable-remediation-status.md` — the tracker; **flip rows as you close them**.
3. `docs/analysis/fable-audit-docket-2026-07-20.md` — the full re-audit: top-10 + findings by
   dimension + UI/UX quick wins. This is your Phase 2 work list, entire.
4. `.claudster/plans/oss-model-lanes-and-public-readiness.md` → Track 0 → the **F12 subtleties**
   block — read before touching worktrees.
5. One previous spec for the house style: `.claudster/prompts/done/docket-reliability-security-implement.md`.

## Hard rules (non-negotiable)
- **docket `main` auto-deploys prod. NEVER push it.** Feature branches only; each merge needs the
  user's explicit go.
- **TDD**: RED test first, then the fix. Commit per finding/fix, only the files it touches.
- Validation gates:
  - claudster: `python -m pytest scripts/tests/ claude-harness/hooks/tests/ -q --import-mode=importlib`
    (baseline **372 passed, 1 skipped**) AND `python validate_pool.py` (must stay OK).
  - docket: `uv run --extra dev pytest -q` (baseline **548 passed** post-`7f612f4`) + `cd web && npx
    vitest run` + `npx tsc --noEmit`. Known flake (NOT a regression):
    `tests/test_api.py::test_create_bug_with_fields_via_api` — re-run before investigating.
- Flip the matching tracker row to DONE in `docs/analysis/fable-remediation-status.md` in the same
  commit as each fix (claudster-side commits) or in a tracker commit per merged branch (docket-side).
- Check in with the user: before **each** docket merge, and before changing any **auth/onboarding
  default** (see Phase 2A).

---

## Phase 1 — claudster: fix pipeline-runner (queue item 6; small, do first)

**Problem:** `.github/pipeline-state.template.json` never survived the extraction from the predecessor
repo. `pipeline_runner.py` reads it **at runtime** (`:967`, `:1523` — the `init` path), so the shipped
tool's `init` is broken for consumers, and 17 of 138 tests fail
(`python -m pytest .github/tools/pipeline-runner/tests/ -q --import-mode=importlib`).

**Do:**
1. Reconstruct the template at `.github/pipeline-state.template.json`. Sources of truth for its shape:
   the fixture in `tests/test_cli_ux.py:33` (writes a template inline) + every field
   `pipeline_runner.py` reads from it + `tests/conftest.py`'s base payload. Reconcile all three; the
   template must make `init` produce a state the rest of the suite accepts.
2. Get the full pipeline-runner suite green: **138 passed, 0 failed** (there is also 1 assertion
   failure beyond the 16 FileNotFoundErrors — diagnose it; it may or may not share the root cause).
3. Wire the suite into the standard gate so it can't rot silently again: add it to the validation
   command documented in `.claudster/relay.md` + the driver prompt, and (if a test-runner config
   exists, e.g. a pytest ini/addopts) include the path there.
4. `validate_pool.py` must stay OK (the template lands in `.github/` — the published pool; keep it
   generic, no internal names/paths).
**Commit:** `fix(pipeline-runner): restore pipeline-state.template.json + green the 138-test suite`
(+ tracker row flip).

---

## Phase 2 — docket: implement the ENTIRE 2026-07-20 re-audit

Work from `docs/analysis/fable-audit-docket-2026-07-20.md` — every finding in §2 (all severities) plus
the §3 UI/UX quick wins. Keep a checklist; anything you deliberately skip must be listed in your final
report with a reason (no silent drops). Suggested slicing — three branches, merged in order so each
rebases on the last:

### 2A — `feat/authz-hardening` (security Highs)
- `unarchive_task` not write-serialized (audit #1) — add to the `@_serialized` wrap-loop
  (`engine.py:1172-1194`); race test.
- Per-project authorization (audit #2) — role becomes per-project-aware; server-side checks on every
  `?project=` read/write (`api.py:733-747, 957-966`).
- NTLM auto-provisioning gate (audit #3 = F20/F21) — `DOCKET_PROXY_SECRET` shared-secret check on the
  proxy header + a provisioning toggle/allowlist. **⚠ Behavior change:** zero-setup onboarding
  (verified in `PUBLIC-READINESS.md` §B3) must stay achievable — propose defaults to the user BEFORE
  implementing (e.g. secret enforced when set, provisioning default-on with an off switch).
- Attachment blob store cross-project readable (audit #9) — scope reads to the requesting user's
  authorized project.

### 2B — `feat/run-safety-2` (pipeline behavior)
- Implement lane gets `requires_confirmation` (audit #4) — reuse the F1 confirm mechanism + lead-only
  UI button. **⚠ Behavior change** (a lead's lane-drag now parks the run until confirmed) — confirm
  the default with the user alongside the 2A defaults.
- Parked (unconfirmed) runs must NOT consume `max_concurrent_runs` slots (audit #7, `engine.py:659-664`).
- Enforce `wip_limits` on `move_task`/`assign_and_advance` (audit #5) — or, if enforcement is
  undesired, remove the dead config surface; ask the user which (one-line question, fold into the 2A
  check-in).
- Lane rename revalidates/warns on orphaned `agent_track.lanes` keys (audit #10).

### 2C — `feat/ux-correctness-2` (everything else)
- Stakeholder card drawer: gate every write control, not just Triage (audit #8).
- All remaining §2 Medium/Low findings + §3 UI/UX quick wins from the report.

Each branch: TDD per finding, full py+web suites green, then STOP → hand to the user for merge
approval (merge = prod deploy). After merge confirmation, verify the Gitea pipeline
(`python_tests → web_checks → deploy`) succeeds before starting the next branch.

---

## Phase 3 — docket F12: full worktree isolation (queue item 5; LAST — riskiest, needs live verify)

**Goal:** an Implement run never touches the human's working tree — no branch switch, no WIP sweep.
Re-confirmed as audit #6: `git checkout -B` on the shared tree carries a dirty tree onto the agent
branch (`runner.py:336-339` per the re-audit; the historic design notes cite `_ensure_feature_branch`).

**Design (from the plan's Track 0 — read the subtleties block first):**
- Replace the in-tree `checkout -B` with `git worktree add <path> -b agent/<slug>`, worktree path under
  `DOCKET_HOME/runtime/worktrees/`.
- Thread the worktree cwd through EVERY `project` use in `_execute_implement` (preflight/implement/
  review spawns, the test run, branch + protected checks).
- **Subtlety 1:** the pipeline reads `.claudster/plans/<slug>.md` (and `PROJECT-FACTS.md`, resolved
  test command) from the working tree — often uncommitted. The worktree impl MUST copy `.claudster/`
  artifacts into the worktree (or commit them first). A fresh worktree from HEAD won't have them.
- **Subtlety 2:** do NOT add a naive "refuse if dirty" gate — docket itself writes those `.claudster/`
  artifacts, so the tree is legitimately dirty on every run; any refusal must scope to changes OUTSIDE
  `.claudster/`.
- `git worktree remove --force` in `finally` + a startup reconcile for orphaned worktrees; keep the
  pre-commit guard (worktrees share `.git/hooks`).
**Verify with a LIVE Implement run, not unit tests alone:** stand up a scratch repo + the fake-harness
fixtures the cross-review e2e already uses (`tests/test_cross_review_gate_e2e.py` — `fake_implement`/
`fake_preflight`/`fake_testcmd` pattern) and assert: the human tree's branch + dirty state are
untouched throughout; the run's commits land on `agent/<slug>`; a crashed run leaves no worktree and
no guard behind (reuse/extend the `_sweep_stale_guard` self-heal).
Branch: `feat/f12-worktree-isolation`. Same merge protocol as Phase 2.

---

## Reporting
End with: per-phase status (done/partial/skipped + why), test counts per repo, every tracker row
flipped, behavior changes shipped (auth defaults, Implement confirmation), and anything from the audit
you deferred with reasons. Update `.claudster/relay.md` (or run `/claudster:handoff`) before ending.
