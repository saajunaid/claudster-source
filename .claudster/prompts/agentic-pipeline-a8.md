# A8 build — the Implement lane (headless plan execution), quality/robustness-first

**Read first:** `E:\Projects\claudster-source\docs\analysis\A8-MINI-PRD.md` — especially "DECISIONS
LOCKED (quality-first)". This prompt implements that design. The overriding rule: **quality, correctness,
and robustness beat cost and simplicity every time.** An autonomous implement can only reach "Validate"
if: plan preflighted clean → code written on an ISOLATED branch → the runner's OWN test run is green →
a fresh code-review found nothing blocking. Correctness is enforced by machinery, never trust.

**How to run:** root at `E:\Projects\claudster-source`, `/add-dir E:\Projects\docket`; **Opus 4.8**;
auto-accept; continue the existing `feat/agentic-pipeline` branches. Baselines: docket
`.venv\Scripts\python -m pytest tests/ -q` (≈377) + `cd web && npm run build && npx vitest run`;
claudster `C:\Python\python.exe -m pytest scripts/tests claude-harness/hooks/tests -q` (244) +
`validate_pool.py`.

**GUARDS-FIRST BUILD ORDER (do not reorder):** build + fully unit-test the orchestration and every safety
gate with FAKES before any live autonomous implement is ever run. The live test (A8.6) is human-run on a
throwaway repo and must demonstrate the guards HOLD.

---

## PROMPT (paste below this line)

You are building the Implement lane (A8) for the docket×claudster pipeline, quality/robustness-first, per
`docs/analysis/A8-MINI-PRD.md` (DECISIONS LOCKED). Continue the existing `feat/agentic-pipeline` branches.
Do NOT publish/push. Do NOT run a live autonomous implement in any automated test — use fakes.

### Non-negotiable safety invariants (assert them in tests) — includes the Fable audit-hardening
1. **Never write on the default branch — enforced at COMMIT, not just spawn.** Refuse to implement unless
   on `agent/<slug>`; install a pre-commit hook that refuses the default branch for the run's duration AND
   post-run verify every new commit landed on the feature branch. Tests prove a default-branch repo is
   refused and a mid-run `checkout main` commit is caught.
2. **Independent test verification is the success gate — with a tamper guard.** The runner runs the test
   command ITSELF after implement (never trusts the session). **Snapshot the test command BEFORE spawning**
   and run that snapshot; **fail the run if the diff touches `.claudster/PROJECT-FACTS.md` or the
   `agent_track.test_command`** (a session must not edit its own success criteria).
3. **Fail if untested.** No determinable test command ⇒ the run FAILS; never mark an untested implement
   succeeded.
4. **Mandatory gates:** preflight (before) MUST PASS before any code; code-review (after) must be
   non-blocking. A review-blocked run gets a distinct **`needs_review`** terminal state — it does NOT
   auto-advance to Validate and must NOT read as a clean success.
5. **Force the guard ON for the implement child.** claudster's PreToolUse guard is the backstop against
   catastrophic actions branch-isolation can't catch. Even though the user runs `CLAUDSTER_GUARD_DISABLED=1`
   globally, the runner MUST delete that var from the spawned implement child's env so the guard runs for
   every autonomous implement. Never run an implement guard-bypassed. A test asserts the child env omits it.

### A8.1 — config (docket)
Extend `agent_track` in `config.py`: `test_command` (str|null), `implement_branch_prefix` ("agent/"),
`implement_timeout_seconds` (3600), `implement_max_turns` (200), `preflight_required` (true),
`review_required` (true). Per-lane Implement override still uses the `__TBD_A8__` command slot — replace
it with the real driver from A8.3 once built (keep the placeholder guard until then). Migration via
`_ensure_agent_track`. Tests: defaults present + migration.

### A8.2 — runner Implement orchestration (docket), FAKE-tested
A distinct execute path for the Implement lane (a mini-pipeline, not one spawn):
`_execute_implement(repo, run)`:
1. Resolve the plan (`.claudster/plans/<slug>.md`) + project repo; **stamp `approval: approved`** on the
   plan (frontmatter merge) — the drag is the approval.
2. **Branch:** ensure the project is on `agent/<slug>` (create from current HEAD if needed). If the repo
   is on its default branch and branch creation fails/refused → **fail the run** (invariant 1).
3. **Preflight:** spawn the harness to validate the plan vs the codebase (a `/claudster:preflight`-style
   headless call, or the preflight agent). Parse PASS/FAIL. FAIL ⇒ fail the run, attach the report.
4. **Implement:** spawn the harness (opus, `implement_*` caps) with the A8.3 driver — TDD, commit per
   phase, update the plan Tracker, write `.claudster/reviews/<slug>.md`, end with a JSON block.
5. **Test (independent):** determine the test command (invariant 3) and RUN it via `_spawn`; capture
   pass/fail. This — not the session — decides success.
6. **Review:** spawn `/claudster:code-review` (or the code-reviewer agent) on the branch diff; parse
   blocking findings.
7. **Gate:** succeeded ⇒ tests green AND review non-blocking; then honor `auto_advance_to: "Validate"`.
   Otherwise fail/hold with the reason (preflight/test/review) surfaced on the run.
Model each step's outcome on the run record (extend the completed/failed events with an
`implement` sub-report: `{branch, preflight, tests, review, phases_done}`). Every failure →
`fail_agent_run`. Wire `_execute` to dispatch to `_execute_implement` when the lane's artifact_dir is null
and the lane is the Implement lane.
**Tests (fakes only):** create `fake_preflight`/`fake_review` stubs (+ reuse `fake_claude` for implement,
`fake_lavish` pattern) and a fake test command. Prove: happy path (all gates pass → succeeded →
advanced); preflight FAIL → failed, not advanced; tests RED → failed; review BLOCKING → not advanced;
default-branch → refused; no test command → failed. Board invariant holds throughout.

### A8.3 — claudster implement driver
Add `/claudster:implement` (`claude-harness/commands/implement.md`) OR a plan-loop over `/tdd`. Headless
contract: read `.claudster/plans/<slug>.md`; work ONLY on the current (feature) branch; implement phases
TDD-first; **commit per phase**; update the `## Tracker`; write a concise `.claudster/reviews/<slug>.md`;
run the tests yourself too; end with `{"implemented":true,"phases_done":N,"tests":"passed|failed",
"review":".claudster/reviews/<slug>.md"}`. Never touch git remotes; never switch off the branch. Content-
lint test (like `test_headless_convention.py`). Then publish (`junai-push` → next plugin version).

### A8.4 — UI (docket web)
Implement run shows phase progress (from the plan Tracker) + a branch/diff affordance in the drawer; the
implement sub-report (preflight/tests/review) rendered; Validate lane shows "review the branch". Build +
vitest.

### A8.6 — GUARDED live test (HUMAN-run; document, do not run in this unattended session)
On a THROWAWAY git repo with a tiny 2-phase approved plan + a real test command, with the 1.3.x plugin
installed: drag Plan→Implement and confirm — (a) it works on `agent/<slug>`, NOT main; (b) it refuses if
forced onto main; (c) it FAILS if the test command is removed; (d) it only advances to Validate on green
tests + clean review. Record results in IMPL-STATUS.md.

### Finish
Gates green both repos; append an A8 section to `docs/analysis/IMPL-STATUS.md` (what shipped, the fake-
test matrix proving the invariants, and the A8.6 human live-test steps left to run); branch/commit report
addendum. Do NOT publish beyond A8.3's plugin bump; do NOT push.

Begin with A8.1, then A8.2 (fake-tested) — the safety invariants must be green before A8.3/A8.4.
