# A8 mini-PRD — the Implement lane (headless plan execution)

**Status:** design pass (no code). **Date:** 2026-07-04. A8 is the "big one" — turning an approved plan
into shipped code. It was deliberately deferred from the main roadmap because it needs decisions the
PRD/Plan lanes didn't. This resolves them against what claudster actually provides, then proposes the
smallest slice.

## DECISIONS LOCKED — quality/correctness/robustness first (2026-07-04)
Per the directive to prioritise quality over cost/simplicity, the defaults are locked as follows — two
are UPGRADED from the original defaults for robustness:
- **D1 driver:** single-session v1 **with commit-per-phase checkpoints** (full-plan context → coherent
  code); per-phase loop is v2, triggered when a plan exceeds ~6 phases (warn + switch).
- **D2 success:** the runner **re-runs the project test suite itself** as the gate, and **FAILS the run
  if no test command can be determined** — never mark an untested implement "succeeded".
- **★ NEW quality gates around implement (the biggest correctness lever) — MANDATORY:** the Implement
  lane is a mini-pipeline, not one spawn:
  **preflight → implement → test → code-review → advance.**
  - **PRE:** run claudster's **preflight** (validate the plan against the real codebase). Must PASS
    before any code is written. (This also satisfies `fast_track`'s preflight requirement.)
  - **POST:** run claudster's **code-reviewer** agent (fresh-context, adversarial) on the diff. Blocking
    findings ⇒ the run does NOT auto-advance to Validate; it surfaces them for the human. (This is the
    "No Mistakes"-style verify pass we discussed early on.)
- **D5 isolation:** **HARD guard — refuse to implement on the default branch.** Always a feature branch
  `agent/<slug>` (git worktree is the v2 upgrade for parallel safety).
- **Approval (D5):** the Plan→Implement drag = the human's approval, **but gated on the preflight PASS** —
  a plan that fails preflight is NOT implemented; the preflight report is surfaced instead.
- **Model:** **opus** for implement (correctness over cost).
- **Test source:** `.claudster/PROJECT-FACTS.md` → `agent_track.test_command` fallback → **fail loudly**
  if neither yields a command (don't guess-and-pass).

Net effect: an autonomous implement can only reach "Validate" if the plan preflighted clean, the code
was written on an isolated branch, the real test suite passes when the runner runs it, AND a fresh
code-review found nothing blocking. Correctness is enforced by machinery, not trust.

## The problem A8 solves
Card dragged **Plan → Implement** ⇒ a headless agent executes the plan (`.claudster/plans/<slug>.md`):
writes code + tests, phase by phase, until the plan is done and the suite is green — then auto-advances
to **Validate** for the human. Unlike PRD/Plan, there is **no single output artifact**, so "success"
must be detected differently.

## Grounded findings (verified in claudster)
1. **`/implement` does NOT exist** as a slash command. There is an **Implement *agent***
   (`.github/agents/implement.agent.md`) — an elite TDD coding agent — but it's a Copilot/ADLC agent
   (model GPT-5.4, Orchestrator handoffs), **not** a `claude -p` slash command.
2. **`pipeline_runner.run_plan` / `fast_track_from_plan` do NOT write code.** They score the plan,
   advance the ADLC *state*, and emit a *handoff* (`next_command: "junai pipeline last-handoff"`). The
   actual coding is done by an agent following that handoff. They also **require** the plan to have
   `approval: approved` frontmatter AND a **PASS preflight** report before entering `implement`.
3. **`/tdd`** is a strict red→green→refactor cycle for **one unit of behavior** — the natural primitive
   for per-phase implementation, but not a whole-plan driver.
4. **The plan's `## Tracker` table** (`| Phase | Model | Status | Commit | Notes |`) is the documented
   **resume/done signal** — "done" = all phases `done` (+ commits).
5. Headless artifacts land in the **linked project repo** (`task.project`), cwd = that repo — same as
   PRD/Plan.

**Consequence:** A8 is not "call one claudster function." The docket runner must (a) drive a headless
coding session against the plan, and (b) detect success from **tests + the Tracker**, not a file.

## The five decisions (with a recommendation each)

### D1 — The driver: single session vs per-phase loop
- **(a) Single headless session (recommend for v1):** one `claude -p` that reads the plan and implements
  ALL phases TDD-style, committing per phase, updating the Tracker, running the tests. Claude Code in
  `-p` can do long multi-step work with its edit/execute/test tools. Simple; the runner just launches +
  verifies.
- (b) Per-phase runner loop (v2): the runner parses the plan's phases and spawns a session per phase
  (or `/claudster:tdd` per behavior), checkpointing via the Tracker + git. Resumable, smaller blast
  radius, but the runner must parse plan structure. Right for big plans.
- **Recommendation:** ship (a) for the smallest slice; evolve to (b) when plans get large.

### D2 — Success signal (no single artifact)
- **Recommend:** success = **the project's test suite passes, run independently by the runner AFTER the
  session** (the harness-neutral truth, mirroring "artifact exists" for PRD) **AND** a review/summary
  file `.claudster/reviews/<slug>.md` exists. The session must also end with a JSON block
  `{"implemented":true,"phases_done":N,"tests":"passed","review":".claudster/reviews/<slug>.md"}` for
  highlights — but the runner **re-runs the tests itself** rather than trusting that block.
- Requires a **test command** (from `.claudster/PROJECT-FACTS.md` or an `agent_track` config key).

### D3 — Long-running + checkpointing
- Implement is minutes, not seconds: raise `run_timeout_seconds` (e.g. 1800–3600) and `max_turns`
  (e.g. 200) for the Implement lane specifically (per-lane overrides in `agent_track.lanes.Implement`).
- The session **commits per phase** (git) so partial progress survives a timeout/crash; the Tracker
  records where it got to.

### D4 — Partial failure / resume
- v1: on failure/timeout, mark the run failed, leave the branch + partial commits; the human inspects.
  Re-dragging (or "Run agent" again) resumes because the plan's Tracker + the code state show what's
  done — the implement prompt says "continue from the first not-done Tracker phase."
- v2: the per-phase loop (D1b) makes resume automatic.

### D5 — The approval gate + isolation
- claudster's `fast_track` needs `approval: approved`. In docket, **moving the card Plan → Implement IS
  the human approving the plan.** So on Implement-lane entry, the runner stamps the plan
  `approval: approved` (frontmatter merge, like `docket_id`) before implementing — connecting the drag
  to claudster's gate.
- **Isolation (important):** implement WRITES code. It must run on a **feature branch, never main.** v1:
  the runner (or the session) creates/uses a branch `agent/<slug>` in the project repo before coding.
  (Ties to claudster's `using-git-worktrees`; a worktree is the v2 upgrade for parallel implements.)

## Smallest valuable slice
A tiny approved plan (2–3 phases) → drag to **Implement** → one `claude -p` session on a `agent/<slug>`
branch implements it TDD-style, commits per phase, updates the Tracker, writes `.claudster/reviews/
<slug>.md` → **the runner re-runs the test command; green ⇒ succeeded ⇒ auto-advance to Validate**;
red/timeout ⇒ failed, branch left for inspection. Human reviews the diff in Validate.

## Open questions for you (decide before building)
1. **v1 driver:** single-session (recommended, simplest) or go straight to the per-phase loop?
2. **Branch strategy:** implement on `agent/<slug>` (runner creates it) — OK? Or a git worktree from the
   start? Or implement in place and rely on the human reviewing before merge?
3. **Test command source:** read from `.claudster/PROJECT-FACTS.md`, or a new `agent_track` config key
   (e.g. `test_command`), or let the agent infer it? (The runner needs it to verify success.)
4. **Approval stamp:** OK for the runner to auto-stamp the plan `approval: approved` on the Plan→Implement
   move (treating the drag as the approval)? Or require an explicit confirm like ISD/Ship?
5. **Model/effort:** which model runs implement under claude-code (opus for correctness vs sonnet for
   cost)? Set via `agent_track.model` or a per-lane override.

## Risks / guards
- **Runaway cost/time:** per-lane timeout + max_turns caps; commit-per-phase; `max_concurrent_runs: 1`.
- **Writing to main:** hard-guard — refuse to implement unless on a non-default branch (defense-in-depth
  like the ISD deploy gate).
- **False "done":** the runner **independently runs the tests** — never trusts the session's own claim.
- **Context blowout on big plans:** single-session (v1) is fine for small plans; the per-phase loop (v2)
  is the answer for large ones — surface a warning when a plan has > N phases.
- **Preflight requirement:** `fast_track` wants a PASS preflight; v1 can bypass `fast_track` and drive
  the coding session directly (preflight becomes an optional pre-step), so we don't block on it.

## Proposed phases (once D1–D5 are decided)
- **A8.1** — config (per-lane Implement overrides: timeout/max_turns/test_command/model; branch policy)
  + the approval-stamp on Plan→Implement.
- **A8.2** — the runner Implement path: branch setup, spawn the implement session, **independent test
  run** for the success signal, review-file detection, auto-advance to Validate on green.
- **A8.3** — claudster: an implement-driver prompt/skill (`/claudster:implement` or reuse `/tdd` in a
  plan-loop) with a strong headless contract (branch, commit-per-phase, update Tracker, write review,
  end with the JSON block). Ship as a new plugin version.
- **A8.4** — UI: Implement run shows phase progress (from the Tracker) + the diff/branch link in the
  drawer; Validate lane shows "review the branch".
- **A8.5 (v2, later)** — per-phase runner loop + worktree isolation + auto-resume.

*Build starts once you answer the 5 open questions. My defaults if you don't want to decide each:
single-session v1 · `agent/<slug>` branch · test command from PROJECT-FACTS (fallback config key) ·
auto-stamp approval on the drag · opus for implement.*
