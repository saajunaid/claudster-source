# Implement — docket reliability & security (Fable F6, F11, F13)

You are a senior backend engineer. Implement the three highest-value OPEN docket findings from the Fable
audit. This is an IMPLEMENTATION task — write the code, test it (TDD where feasible), and verify. Work in
`E:\Projects\docket` (backend under `src/docket/`, frontend under `web/src/`).

Source: `E:\Projects\claudster-source\docs\analysis\fable-audit-docket-2026-07-15.md` (F6, F11, F13) and the
status tracker `…\docs\analysis\fable-remediation-status.md`. Read those rows first.

## Ground rules
- **Branch:** create `feat/reliability` off the CURRENT `main` (which already has F1/F17/F12-partial + a11y).
  **NEVER push docket `main`** — a push to `main` auto-deploys prod via the Gitea pipeline.
- **Tests:** run `.venv\Scripts\python.exe -m pytest tests/ -q` after each phase (use the venv python directly;
  `uv run` may fail on a locked `docket.exe` if a docket process is running). Web: `cd web; npx vitest run`.
  The full suite is ~496 py + 143 web. **Heads-up:** `tests/test_api.py::test_create_bug_with_fields_via_api`
  is a KNOWN pre-existing flake (intermittent 500 from Windows subprocess/file timing) — if it fails, re-run;
  it is NOT your regression.
- **Commit per phase**, only the files that phase touches. Update the two `fable-remediation-status.md` rows
  (in the claudster repo) to DONE when each lands.

## Phase 1 — F6: gate verdicts are spoofable via transcript content (security)
Today `_preflight_verdict` / `_review_verdict` (`src/docket/runner.py` ~482-504) substring-match `REVIEW: CLEAN`
/ `PREFLIGHT: PASS` (and the blocking markers) over the WHOLE agent transcript. A task description, bug text,
or a code comment that merely *contains* `REVIEW: CLEAN` flips a fail-closed gate open — and task/bug content
is attacker-controllable (any contributor; bug text by any authenticated user).
- **Fix:** anchor the positive verdict to the **final non-empty line** of the agent's output (the prompts
  already demand "end with EXACTLY one line and nothing after it"). A marker appearing *anywhere but the last
  line* must NOT count as a positive — return `None` so the fail-closed classifier decides. Keep the existing
  "any blocking signal beats any clean signal" rule (blocking may still match anywhere — fail-closed).
- **TDD (RED first):** a transcript whose BODY contains `REVIEW: CLEAN` but whose last line is a blocking/other
  verdict must NOT pass; a transcript ending in exactly `REVIEW: CLEAN` passes; injected `PREFLIGHT: PASS` in a
  quoted plan snippet must not pass. Mirror the existing verdict tests.
**Commit:** `fix(runner): anchor gate verdicts to the final line — task/commit text can't spoof CLEAN/PASS (F6)`

## Phase 2 — F11: cross-process race on `.docket/` (data integrity)
`engine` serializes writes with in-memory `threading.RLock` only (`src/docket/engine.py`), but the shipped
hooks (`docket hook …`), CLI (`docket run`/`docket sync`), and the dev-agent-worker all write `.docket/` from
SEPARATE processes. Two processes can read the same `id_counter` → allocate the same `DKT-N`, or interleave
`board.json` rebuilds → violating the §10 "ids never reused" / `reduce(events)==board` invariants.
- **Fix:** add an **on-disk file lock** around the commit+allocate critical section (the `@_serialized`
  boundary — `_commit` / `_allocate`). Use a cross-platform lock on a `<repo>/.docket/.lock` file: prefer
  `msvcrt.locking` on Windows + `fcntl.flock` on POSIX behind a tiny context manager (or add `portalocker` as a
  dep if you'd rather — check `pyproject.toml`). Acquire OUTSIDE the in-memory lock, hold across read-counter →
  append → rebuild, release in `finally`. Keep the in-memory lock too (fast path for same-process threads).
- **TDD:** a test that spawns two processes (or uses the lock directly) racing `queue`/`create_task` on one
  repo must yield **distinct** ids and a consistent board — the current code fails this. Keep it deterministic
  (a subprocess helper or a monkeypatched lock that proves mutual exclusion).
**Commit:** `fix(engine): on-disk file lock around commit+allocate — no duplicate ids across processes (F11)`

## Phase 3 — F13: stuck runs wedge the WIP cap (reliability)
Orphan/stale reconcile runs ONLY at process startup (`src/docket/api.py` lifespan). A dead remote worker or a
hung local run holds `running` forever; since the cap counts `queued`+`running`, every new enqueue then 409s
(explicit) or is silently dropped (lane trigger) with no runtime recovery.
- **Fix (two parts):**
  1. A **periodic reconcile** task (in the FastAPI lifespan, e.g. every ~60s) that runs the same stale-heartbeat
     / orphan reaping the startup path already does (`runner` reap helpers ~720-751) — so a wedged run clears
     without a server restart. Make the interval configurable (`agent_track.worker_heartbeat_timeout` /
     a new knob) and shut the task down cleanly on lifespan exit.
  2. A **lead-only cancel/fail endpoint** (`POST /api/tasks/{id}/runs/{rid}/cancel` or `/fail`) → emits
     `agent.run.failed` with a clear reason, freeing the slot; plus a **"Cancel run" button** in Command Center
     on a `running`/`queued` run (reuse the existing `btn` classes — do NOT add new CSS; `web/src/components/
     CommandCenter.tsx` already has the confirm-button pattern + an aria-live region, extend consistently).
- **TDD:** a run whose heartbeat is stale is reaped by the periodic pass (not just startup); the cancel
  endpoint frees the cap and is rejected for non-leads; a web test for the button if feasible.
**Commit:** `feat(runner+api): periodic stuck-run reconcile + lead-only cancel endpoint & Command Center button (F13)`

## Verification (before done)
- Full py suite green (mind the known bug-create flake — re-run if it trips) + web build clean + web tests.
- For F13, sanity-check the periodic task actually fires (log line / a short-interval test) and the cancel
  button works end-to-end against the dev server.
- Write a short results note into docket `docs/analysis/`.

## Output
A `feat/reliability` branch, one commit per phase, suites green, results note. Do NOT push `main` — hand the
branch back for review/merge (merging `main` deploys prod). Flag anything left partial (e.g. F11's
multi-process test if the harness is awkward on Windows).
