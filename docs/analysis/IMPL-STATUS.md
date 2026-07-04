# Implementation status — claudster × docket agentic pipeline (first slice)

**Run:** autonomous, unattended, per `.claudster/prompts/agentic-pipeline-impl.md`.
**Date:** 2026-07-04. **Scope built:** Track 0 → A1 → A3 → A2 (nothing else). **Result:** all four
phases complete, every gate green, no publish, no live `claude -p`, no pushes/PRs.

---

## Phases completed

| Phase | Repo | Branch | Commit | Gate |
|---|---|---|---|---|
| **Track 0** — publish safety | claudster-source | `feat/agentic-pipeline` (base `main`) | `2f06fae` | ✅ pytest 242 · export 0 · validate_pool default+claude+claude-extras OK |
| **A3** — `/prd` headless convention | claudster-source | `feat/agentic-pipeline` | `4796334` | ✅ pytest 242 · validate_pool default+claude OK |
| **A1** — `agent.run.*` events + reducer + records | docket | `feat/agentic-pipeline` (base `main`) | `0874f99` | ✅ pytest (full suite 329 after A1) · determinism replay==board.json |
| **A2** — agent-runner + harness adapter + lane trigger | docket | `feat/agentic-pipeline` | `d088823` | ✅ full suite **357 passed** · fake_claude scenarios · opt-in/layering/Windows-kill |

### What each phase shipped
- **Track 0** (`sync.ps1`, `validate_pool.py`, `README.md`, `.github/runtime-targets.json`):
  inverted `junai-push` publish default → **publish is opt-in via `-Publish`** (`-NoPublish` is now a
  deprecated silent no-op); added a **SHA256 content-diff gate** inside `junai-release`
  (`.last-published-{mcp,ext}.sha256` markers; `-Force` bypass) so an unchanged MCP/extension is never
  re-uploaded; new **`validate_pool.py --profile claude|claude-extras`** plugin-bundle validator
  (checks a–f: plugin.json shape+version/name match, flattened SKILL.md frontmatter + roster, commands/
  agents/hooks present, hooks.json refs resolve, leak scan, **scripts/ ships every module the hooks
  import**). Check (f) caught the live **Dream Memory bug** (hooks import `dream_memory`/`dream_capture`
  from `scripts/`, never packaged) — fixed by adding the 3 scripts to the `claude` target's `files`
  (see Open questions #1). `-Publish` gating verified by **reading** the code; `junai-push` was **not
  run** (hard rule).
- **A3** (`claude-harness/commands/prd.md`): added a `## Headless mode` section — the `HEADLESS RUN
  RULES` marker suspends the interview (no AskUserQuestion, derive-don't-ask, unresolved → `## Open
  questions`, honor caller `artifact_dir`+`feature` slug, end with one fenced json highlights block).
  Interactive flow + frontmatter unchanged.
- **A1** (`events.py`, `ids.py`, `reducer.py`, `engine.py`, `docket-build-spec.md` §11, `.gitignore`,
  tests): 4 `agent.run.*` event types (`actor="runner"`), `new_run_id()`, board `runs{}` map + tasks
  `agent_runs`/`last_run`, 4 pure reducer handlers, 4 `@_serialized` engine ops. TDD (15 tests).
- **A2** (`harness.py`, `runner.py`, `config.py`, `engine.py`, `api.py`, `cli.py`, `fake_claude.py`,
  tests): `ClaudeCodeAdapter` (Gemini/Codex stubs), `Runner` (daemon worker + `run_now` sync +
  `enqueue` async, cap→409, Windows CTRL_BREAK timeout-kill, artifact+frontmatter success signal,
  post-hoc `docket_id` merge, fail-soft highlights), engine lane-trigger registry wired into
  `move_task`, §C2 config + migration, §C5 API endpoints + board decoration + runner in lifespan,
  `docket run` CLI. Tested via `fake_claude.py` only (ok/no_artifact/hang/error) — 28 new tests.

---

## Human-required gates left undone (deferred per the unattended-run safety rules)

These need a human with API keys / a live harness / publish creds. **None are blockers to the code;**
they are the live-smoke + publish steps the run was forbidden to perform.

1. **A3 publish → plugin 1.3.15.** Run `junai-push -NoPublish` in `E:\Projects\claudster-source`
   (mirror sync + version bump, **no** MCP/VS Code release). This ships the `prd.md` headless section
   **and** the 3 Dream Memory scripts (see Open questions #1). Verify plugin **1.3.15** in the mirror.
   *Not run here (hard rule: no `junai-push`).*
2. **B1 live smoke (A2):** `claude -p "Say OK" --output-format json` non-interactive with
   `ANTHROPIC_API_KEY` under the Windows service context — proves auth.
3. **B2 live smoke (A2 + A3):** `claude -p "/prd smoke" --output-format json` produces the artifact and
   shows **zero interview turns** — proves plugin+slash-command discovery in `-p` and the headless
   convention end-to-end.
4. **A2 real end-to-end:** `docket run DKT-<n>` on a real repo (agent_track enabled, real `claude`) →
   run reaches `succeeded` with a real `.claudster/prd/<slug>.md`.
5. **Track 0 manual evidence (optional):** a `junai-push` transcript (keys present) showing it ends
   with **no publish lines** — the gating was verified by reading the code, not by executing it.

---

## Open questions

1. **Dream Memory packaging fix was applied as a Track 0 companion (technically Track C-3 scope).**
   Track 0's check (f) is *designed* to catch the bug where the hooks import `dream_memory`/
   `dream_capture` but those scripts were never copied into the bundle. With the bug present,
   `validate_pool.py --profile claude` FAILS — so Track 0 could not pass its own gate. Since the source
   files already existed (`claude-harness/scripts/{dream_memory,dream_capture,claudster_config}.py`) and
   the roadmap explicitly says check (f) "locks" this fix (C-3), I added the 3 files to the `claude`
   target's `files` in `runtime-targets.json` — the minimal fix that makes the gate green and the layer
   actually work. **This changes the shipped bundle** (it will ride the next publish and bump the plugin
   version). If you would rather ship the validator *without* the packaging change, revert the
   `runtime-targets.json` hunk and expect `--profile claude` to fail until C-3 lands separately.
2. **Plugin version is still 1.3.14 in the manifest** (Track 0 + A3 changed content but nothing was
   published). The only *bundle-content* changes this session are `prd.md` (A3) + the 3 dream scripts;
   `sync.ps1`/`validate_pool.py` are repo tooling and do **not** ship. Next `junai-push -NoPublish`
   bumps to 1.3.15 and ships those two.
3. **`docket run` needs a lane with a command.** The CLI defaults to the task's *current* lane; a task
   sitting in a human lane (e.g. `Validate`) raises `InvalidOperation`. Pass `--lane PRD` explicitly, or
   the daemon path (lane move) handles it via the trigger. Documented, not a defect.
4. **Windows timeout-kill is exercised only via the fake stub.** The CTRL_BREAK + 5s-grace + kill path
   passed against `fake_claude.py hang`, but has not been validated against a real long-running
   `claude -p`. B1/B2 above cover this.

---

## Global quality gate — state at end of run

- **Determinism:** `reduce(read_events()) == board.json` after every agent-run write path
  (`test_board_json_equals_replay_after_agent_run_writes`). ✅
- **Both suites green:** docket `.venv\Scripts\python -m pytest tests/ -q` → **357 passed**; claudster
  `python -m pytest scripts/tests claude-harness/hooks/tests -q` → **242 passed** +
  `validate_pool.py` (default + `--profile claude` + `--profile claude-extras`) all **OK**. ✅
- **Layering:** runner calls engine ops only (never `store.append_event`); reducer pure; API/CLI thin;
  no writer touches `events.jsonl` outside `engine._commit`. ✅ (grep-verified)
- **Opt-in safety:** with `agent_track.enabled=false`, dragging a task across all lanes emits **zero**
  `agent.run.*` events (`test_disabled_agent_track_emits_zero_run_events_across_all_lanes`). ✅
- **Windows-first:** `CREATE_NEW_PROCESS_GROUP` + `CTRL_BREAK_EVENT` spawn; separator-tolerant path
  compares (`Path.resolve().relative_to`); no pytest-xdist. ✅
- **Harness-neutral:** success = artifact exists + frontmatter (`type`+`feature`) parses, never an exit
  code; `cost_usd`/`num_turns`/`session_id` nullable. ✅

---

## How to resume (exact next commands)

**Ship this slice (human, keys present):**
```powershell
cd E:\Projects\claudster-source
junai-push -NoPublish          # → plugin 1.3.15 (mirror sync + bump; NO MCP/VS Code release)
# then B1/B2 live smokes, then the real docket run E2E (gate #4 above)
```

**Continue the roadmap (next phase per the dependency graph `A1→A2→A4`):**
`A4 — render-back UI + oli.index.md` (docket web + `src/docket/oli_index.py` §C7). Completes the
OLI→PRD headless slice. See `docs/analysis/ROADMAP.md` §A4.

**Branches are local only** — no remote pushes, no PRs (hard rule). Review, then push/PR at your
discretion:
```powershell
cd E:\Projects\claudster-source; git push -u origin feat/agentic-pipeline
cd E:\Projects\docket;            git push -u origin feat/agentic-pipeline
```

---

## Branches & commits (raw, verbatim — mandatory addendum)

```
############## CLAUDSTER (E:\Projects\claudster-source) ##############
$ git branch --show-current
feat/agentic-pipeline

$ git log --oneline main..HEAD
4796334 feat(claudster): A3 /prd headless-mode convention
2f06fae feat(claudster): Track 0 — publish safety (opt-in publish + content-diff gate + plugin-bundle validator)

$ git status --short
 M .github/agent-docs/agent-eval.md      # PRE-EXISTING (dirty at session start; NOT part of this run)

############## DOCKET (E:\Projects\docket) ##############
$ git -C E:\Projects\docket branch --show-current
feat/agentic-pipeline

$ git -C E:\Projects\docket log --oneline main..HEAD          # base = main
d088823 feat(docket): A2 agent-runner + harness adapter + lane trigger
0874f99 feat(docket): A1 agent.run.* events + reducer + run records

$ git -C E:\Projects\docket status --short
 M .gitea/scripts/CLAUDE.md      # PRE-EXISTING (dirty at session start; NOT part of this run)
 M kb/deployment.md              # PRE-EXISTING
 M relay.md                      # PRE-EXISTING
 M src/docket/CLAUDE.md          # PRE-EXISTING
?? .claudster/memory.jsonl       # PRE-EXISTING (untracked)
?? .claudster/usage-log.jsonl    # PRE-EXISTING (untracked)
```

### Per-repo summary
- **claudster-source:** branch `feat/agentic-pipeline`, forked from **`main`**, **2 commits added**
  (`2f06fae`, `4796334`). Working tree is **clean except one pre-existing** modified file
  (`.github/agent-docs/agent-eval.md`) that was already dirty at session start and is out of scope —
  **not touched by this run**.
- **docket:** branch `feat/agentic-pipeline`, forked from **`main`**, **2 commits added** (`0874f99`,
  `d088823`). Working tree has **only pre-existing** dirty/untracked files (4 modified docs +
  2 untracked `.claudster/*.jsonl`), all present at session start and **not touched by this run**.
- Both branches were created in this run; no remote was pushed; no PR opened; nothing merged.

---

## Reviewer validation + updates (2026-07-04, separate session)

**Independent verification:** both suites re-run from scratch — docket **357 passed**, claudster **242
passed** (system Python `C:\Python`; the `.venv` lacks pytest), `validate_pool.py` default + `--profile
claude` OK. Code-reviewed the high-risk A2 files: adapter seam clean (Claude not hardcoded; Gemini/Codex
stubs raise loudly), runner double-wrapped so a run never sticks in `running`, `_maybe_enqueue_agent_run`
swallows trigger errors so a move never breaks, opt-in test asserts BOTH zero events AND trigger-never-
fired. **Verdict: PASS.**

**B1 smoke PASSED (run by the reviewer, this machine, logged-in session — no API key):**
`env -u CLAUDECODE claude -p "…" --output-format json --max-turns 1` → clean envelope
`{is_error:false, result:"OK", num_turns:1, session_id:…, total_cost_usd:…}`. Confirms auth + headless +
CLAUDECODE-strip work, AND that the real envelope carries exactly the fields `ClaudeCodeAdapter.
parse_result` reads (`is_error`/`total_cost_usd`/`num_turns`/`session_id`/`result`). Adapter mapping
verified against live output. **B2 (headless `/prd`) PASSED (run by reviewer, 2026-07-04, after 1.3.15 shipped + installed):**
`claude -p "/claudster:prd smoke-echo-cli … HEADLESS RUN RULES …"` → `is_error:false`, `num_turns:4`,
wrote `.claudster/prd/smoke-echo-cli.md` with correct frontmatter (`type:prd`, `feature:smoke-echo-cli`),
emitted the highlights json block, **zero interview** (3 items under `## Open questions`). The headless
convention (A3) + plugin-loading in `-p` + adapter field mapping are all proven end-to-end.

**Real docket-run E2E PASSED (reviewer, 2026-07-04):** `runner.run_now` → real `claude -p /claudster:prd`
→ **status succeeded**, artifact `.claudster/prd/e2e-echo-cli.md` written, events `queued→started→
completed`, `docket_id: DKT-1` merged into frontmatter by the runner, highlights parsed. The full runner
loop is proven against real claude on Windows.

**TWO production bugs caught by live testing (runner fails 100% on Windows without both). Fake_claude
missed both. Both proven-fixed in the E2E; folded into A4 Task 0:**
1. **Command namespacing** — bare `/prd` does NOT resolve in `claude -p` ("Unknown command: /prd. Did you
   mean /pdf?"); only `/claudster:prd` works. Fix docket `config.py` DEFAULT_CONFIG →
   `/claudster:{prd,feature-plan,ship}`. ROADMAP §C2 updated.
2. **Windows exe resolution** — `subprocess.Popen(["claude", …])` → `FileNotFoundError [WinError 2]`
   because `claude` is a `.CMD` shim; Popen does no PATHEXT resolution. Fix `runner.py`: resolve via
   `shutil.which(cmd) or cmd` before spawn. ROADMAP §C4 updated.

Note: the runner's failure-handling is CONFIRMED — the first (unresolved-exe) E2E failed cleanly with
`queued→started→failed` and a captured error, no stuck run. Minor follow-up: `cost_usd` came back null
via the runner (B2 direct showed it populated) — nullable by design; low priority.

**LIVE UI DEMO (reviewer, 2026-07-04) — the A4 slice works on screen.** Ran `docket serve` + the Vite
SPA against an agent-track board; moved a card Ideas→PRD via the API (= the drag lane-trigger); the UI
rendered the ⚡ AGENT lane pill, the per-card run-status dot, and live-polled the run to completion. A
described card (DKT-2) → **run succeeded (88s), PRD written, `docket_id: DKT-2` merged, `oli.index.md`
generated, green status dot**. Screenshots: S1 idle, S3 completed (DKT-1 red / DKT-2 green). A4 UI
CONFIRMED live.

**CRITICAL FINDING (highest priority for the OLID vision) — headless `/prd` interviews on terse input.**
The FIRST demo card (DKT-1: 3-word title, **no description**) FAILED: `claude -p` returned questions
("A few questions to scope this before I write the PRD…") instead of writing the artifact — the A3
headless convention did NOT suppress the interview. B2/E2E passed only because their cards had a
description. **This is the core OLID use case** ("post a one-line idea"), so the current prd.md headless
section is not yet robust enough. **Fix (claudster-side, before the OLID flow ships): strengthen the
`## Headless mode` section in `claude-harness/commands/prd.md` (and `feature-plan.md`) to NEVER ask under
the marker — even with a bare one-line title, write a best-effort PRD deriving sensible defaults and put
ALL unknowns under `## Open questions`.** Add a regression: a title-only headless run must produce an
artifact with zero questions. This is the interview-vs-derive robustness the OLID pipeline depends on.

**Open finding #5 — cap-check TOCTOU race (minor; being fixed next session).** `runner._create_run`
reads `_active_count` then calls `queue_agent_run` — not atomic, so two near-simultaneous enqueues could
both pass when `max_concurrent_runs=1`. Effect: transient "2 ran when cap said 1"; no crash/corruption;
negligible for solo WIP=1 but real at Milestone M1. **Fix (decided): move cap enforcement INTO the
serialized `queue_agent_run` engine op** so check+append are atomic under the lock. Bundled into the A4
session (see `.claudster/prompts/agentic-pipeline-a4.md`).

---

## A4 session (2026-07-04) — render-back UI + oli.index.md + cap-race fix

**Docket-only**, continuing docket `feat/agentic-pipeline`. All three tasks shipped; every gate green.
claudster untouched this session.

### Shipped (docket, 3 commits on `feat/agentic-pipeline`)
- **`4640848` — Task 0: two live-caught Windows production fixes.**
  (0a) `config.py` agent-lane commands namespaced `/prd`→`/claudster:prd`, `/feature-plan`→
  `/claudster:feature-plan`, `/ship`→`/claudster:ship` (bare `/prd` doesn't resolve in `claude -p`);
  config-derived test assertions updated. (0b) `runner._execute` resolves the exe via
  `shutil.which(cmd) or cmd` before `build_argv` (`claude` is a `.CMD` shim; Popen does no PATHEXT
  resolution → `FileNotFoundError [WinError 2]`). New test: argv[0] is the resolved path.
- **`0d06aed` — Task 1: cap-race fix (finding #5).** `max_concurrent_runs` enforcement moved INTO the
  serialized `queue_agent_run` engine op, so the active-count check and the `agent.run.queued` append
  are atomic under the per-repo write lock. `OverCapacity` moved to `engine` (runner re-exports it → API
  409 mapping + all imports unchanged); `runner._create_run` dropped the racy pre-check + unused
  `_active_count`. New engine test asserts `queue_agent_run` itself raises at cap; `test_over_cap_raises`
  stays green.
- **`f7af299` — Task 2: A4 render-back UI + `oli.index.md`.**
  Backend (§C7): `oli_index.py::project_oli_index` writes a read-only `.docket/oli.index.md` Ideas-lane
  table, hooked best-effort into `engine._commit` (never raises; content-diffed → no churn on non-Ideas
  commits). Frontend (React Query only, plain CSS vars): `Run`/`Board.runs`/`Board.agent_track`/
  `Artifact` types; `runTask`/`getRuns`/`getRun`/`getArtifact` client fns; `useRuns`; `useBoard` polls 2s
  ONLY while a run is queued/running; `lib/runStatus` pure chip mapping; Lane ⚡ pill; Card status dot
  (queued gray / running pulsing amber / succeeded green / failed red); CardDrawer "Agent runs" section
  (list + Run button + Open artifact); `ArtifactView` renders frontmatter + GFM body via react-markdown
  + remark-gfm.

### Gate results (all green)
- `docket .venv\Scripts\python -m pytest tests/ -q` → **368 passed** (357 baseline + 2 cap + 9 oli).
- `cd web && npm install && npm run build` (tsc --noEmit + vite) → **OK** (833 kB bundle; pre-existing
  >500 kB chunk-size *warning* only — react-markdown adds weight; non-fatal).
- `cd web && npx vitest run` → **65 passed** (added: 4 run-status chip mapping + 4 client run/artifact
  encoding tests).
- Determinism: `reduce(read_events()) == board.json` after the oli_index hook
  (`test_determinism_holds_after_oli_index_hook`). ✅
- Opt-in safety: `enabled=false` → zero `agent.run.*` across all lanes
  (`test_disabled_agent_track_emits_zero_run_events_across_all_lanes`, still green) AND no oli.index
  churn on non-Ideas commits (`test_non_ideas_commit_does_not_churn_the_index`). ✅

### Human-required A4 evidence (OUT of scope this run)
- **Live drag→PRD slice recording:** a screen recording of drag a card into the PRD lane → pulsing amber
  dot → green chip + cost → rendered PRD in the drawer, and `.docket/oli.index.md` generated. Needs the
  running docket web + a real `claude` (plugin **1.3.15**, already installed) with an agent_track-enabled
  repo. This is the OLI→PRD slice's visible acceptance; the code path is proven by the A2 real-`claude`
  E2E (reviewer session) + the A4 unit/build gates, but the on-screen recording was not captured
  (unattended run: no live agent, no browser driving).

### Open questions
1. **Web bundle size** — adding react-markdown pushed the single JS chunk to ~833 kB (gzip 242 kB),
   tripping vite's >500 kB warning (non-fatal, pre-existing threshold). If it matters, code-split
   `ArtifactView`/react-markdown behind a dynamic `import()` (A6 command-center work is a natural point).
   Deferred — not a gate failure.
2. **⚡ agent pill gating** — the pill (and the drawer "Run agent" button) render only when
   `agent_track.enabled` AND the lane is a configured agent lane, so a default board (Triage/Inbox/…,
   track off) shows nothing. The literal §C5 wording is "lanes in `agent_track.lanes`"; I gated on
   `enabled` too for honest UX (a disabled track's Run button would 400). Flag if you want pills shown
   while disabled.
3. **Implement lane Run button suppressed** — `canRunAgent` excludes `command === "__TBD_A8__"`, so the
   Implement lane shows no Run button (it would be a guaranteed-fail until A8 wires the real driver).

### Next per the dependency graph
`A5` (lavish, spike-gated by S0) or `A6` (command-center view) — see `ROADMAP.md`. The OLI→PRD headless
slice is now code-complete (A1→A2→A4); only the live drag→PRD recording remains as human evidence.

---

## Branches & commits (A4 session — raw, verbatim)

```
############## CLAUDSTER (E:\Projects\claudster-source) ##############
$ git branch --show-current
feat/agentic-pipeline

$ git log --oneline main..HEAD
0833d98 docs: B2 + E2E live smokes PASSED; 2 Windows/plugin bugs caught + fixes specced
a5f159a chore(claudster): bump manifest version (claudster v1.3.15)
438dd06 docs: reviewer validation (PASS + B1 smoke green) + A4/cap-race prompt
bd359e8 docs(analysis): IMPL-STATUS handoff — Track 0/A1/A3/A2 complete, gates + human-required steps
4796334 feat(claudster): A3 /prd headless-mode convention
2f06fae feat(claudster): Track 0 — publish safety (opt-in publish + content-diff gate + plugin-bundle validator)
# NOTE: bd359e8/438dd06/a5f159a/0833d98 are prior/reviewer-session commits — the A4 session made NO claudster changes.

$ git status --short
 M .github/agent-docs/agent-eval.md      # PRE-EXISTING (dirty at session start; NOT part of any run)

############## DOCKET (E:\Projects\docket) ##############
$ git -C E:\Projects\docket branch --show-current
feat/agentic-pipeline

$ git -C E:\Projects\docket log --oneline main..HEAD          # base = main
f7af299 feat(docket): A4 render-back UI + oli.index.md
0d06aed fix(docket): enforce max_concurrent_runs atomically in queue_agent_run (cap-race)
4640848 fix(docket): namespace agent commands + resolve exe via shutil.which (Windows) — live-caught
d088823 feat(docket): A2 agent-runner + harness adapter + lane trigger
0874f99 feat(docket): A1 agent.run.* events + reducer + run records

$ git -C E:\Projects\docket status --short
 M .gitea/scripts/CLAUDE.md      # PRE-EXISTING
 M kb/deployment.md              # PRE-EXISTING
 M relay.md                      # PRE-EXISTING
 M src/docket/CLAUDE.md          # PRE-EXISTING
?? .claudster/memory.jsonl       # PRE-EXISTING (untracked)
?? .claudster/usage-log.jsonl    # PRE-EXISTING (untracked)
```

### Per-repo summary (A4 session)
- **claudster-source:** branch `feat/agentic-pipeline`. **0 commits added this session** (docket-only run).
  The 6 commits shown are from Track 0/A3 + the reviewer session. Working tree: only the pre-existing
  `.github/agent-docs/agent-eval.md` is dirty — untouched by this run.
- **docket:** branch `feat/agentic-pipeline`, base `main`. **3 commits added this session** (`4640848`,
  `0d06aed`, `f7af299`) on top of A1/A2. Working tree has only pre-existing dirty/untracked files
  (4 modified docs + 2 untracked `.claudster/*.jsonl`) — none touched by this run. No remote pushed, no
  PR, nothing merged.
