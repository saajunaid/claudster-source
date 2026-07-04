# Autonomous implementation prompt — A4 (render-back UI + oli.index.md) + cap-race fix

**What this is:** the next unattended Claude Code session, continuing the agentic-pipeline slice. It
does the cap-race hardening (docket engine) and Phase A4 (docket web render-back + `oli.index.md`),
completing the *code* for the visible OLI→PRD loop. All work is **docket-only** (no claudster changes).

**How to run:**
- Root the session at `E:\Projects\claudster-source`, then `/add-dir E:\Projects\docket` (all work is
  in docket, but keep the ROADMAP reachable for the §A4/§C7 schemas).
- Model: **Opus 4.8**; enable auto-accept edits.
- Continue on the EXISTING branch `feat/agentic-pipeline` in docket (created last run — do NOT make a
  new branch). claudster stays untouched this session.
- Prereqs already merged on that branch: A1 (events/reducer) + A2 (runner/adapter/API). Verified green.

---

## PROMPT (paste everything below this line)

You are continuing the claudster×docket agentic-pipeline build, AUTONOMOUSLY and unattended. This
session is DOCKET-ONLY. Work in E:\Projects\docket (its own git repo, its own .venv). Node/npm is
required for the web work. Platform: Windows / PowerShell.

### Source of truth (read first)
- E:\Projects\claudster-source\docs\analysis\ROADMAP.md — read §C1–§C7 (normative contracts, copy
  verbatim), §A4 (the render-back phase), and §Q (global quality gate).
- E:\Projects\claudster-source\docs\analysis\IMPL-STATUS.md — current state; A1/A2 are merged and green
  on docket `feat/agentic-pipeline`; open finding #5 is the cap-race you will fix.

### Branch
Continue on the EXISTING docket branch `feat/agentic-pipeline` (do NOT create a new branch, do NOT
touch claudster). Confirm you are on it before editing. Commit per task below.

### Baseline (confirm green before starting)
`E:\Projects\docket\.venv\Scripts\python -m pytest tests/ -q` → expect 357 passed. If red, STOP.

### Task 0 — two live-caught production fixes (REQUIRED; the runner fails 100% on Windows without these)
Both were found by real `claude -p` smoke + docket-run E2E on 2026-07-04 (see IMPL-STATUS). fake_claude
could not catch either.

**0a — namespace agent-lane commands.** Bare `/prd` does NOT resolve in `claude -p` ("Unknown command:
/prd. Did you mean /pdf?"). In `src/docket/config.py` `DEFAULT_CONFIG.agent_track.lanes`, set:
`PRD → "/claudster:prd"`, `Plan → "/claudster:feature-plan"`, `Ship → "/claudster:ship"` (Implement stays
`__TBD_A8__`). Update any test asserting the old bare command.

**0b — resolve the executable for Windows.** `subprocess.Popen(["claude", …])` fails with
`FileNotFoundError [WinError 2]` because `claude` is a `.CMD` shim (`shutil.which("claude")` →
`…\npm\claude.CMD`) and Popen does no PATHEXT resolution. Fix in `src/docket/runner.py`: resolve the
command via `shutil.which(cmd) or cmd` before building argv (where `cmd = agent.get(_CMD_KEY…)` in
`_execute`). Add a test: with `claude_cmd` a bare name, the runner resolves it via a monkeypatched
`shutil.which` before spawn. (Verified live: once resolved + namespaced, the full E2E goes
queued→started→completed with the artifact written and `docket_id` merged.)

Commit: `fix(docket): namespace agent commands + resolve exe via shutil.which (Windows) — live-caught`.

### Task 1 — cap-race fix (engine hardening)
Move `max_concurrent_runs` enforcement from `runner._create_run` INTO the serialized engine op
`queue_agent_run` (in `src/docket/engine.py`), so the active-run count check and the `agent.run.queued`
append happen atomically under the same per-repo write lock. Then simplify `runner._create_run` to rely
on the engine op (it may keep a cheap pre-check for a fast 409, but the AUTHORITATIVE cap check must be
inside `queue_agent_run`). `queue_agent_run` raises `runner.OverCapacity` (or an engine exception the
API maps to 409 — keep the existing 409 mapping working). Add a test asserting `queue_agent_run` itself
raises when already at cap (not just the runner wrapper). Keep the existing `test_over_cap_raises`
green. Commit: `fix(docket): enforce max_concurrent_runs atomically in queue_agent_run (cap-race)`.

### Task 2 — Phase A4: render-back UI + oli.index.md
Implement exactly per ROADMAP §A4 + §C7. Files:
- `src/docket/oli_index.py` (new, §C7): `project_oli_index(repo_path, board)` writes a read-only
  `.docket/oli.index.md` markdown table of non-archived cards in the **Ideas** lane
  (`| ID | Title | Lane | Created |`), header "generated — do not edit". Call it best-effort from
  `engine._commit` on events touching Ideas-lane cards (never raises). Add tests.
- `web/package.json` — add `react-markdown` + `remark-gfm` (run `npm install`).
- `web/src/api/types.ts` — `Run` type (§C3 record), `Task.agent_runs?`/`last_run?`, `Board.runs`,
  `Board.agent_track?` (§C5 decoration).
- `web/src/api/client.ts` — `runTask(taskId, lane?)`, `getRuns(params)`, `getRun(id)`,
  `getArtifact(path, project?)`.
- `web/src/hooks/useRuns.ts` (new); `web/src/hooks/useBoard.ts` — conditional `refetchInterval: 2000`
  ONLY while any board run is `queued|running` (else off — no idle polling).
- `web/src/components/Lane.tsx` — "⚡ agent" pill on lanes in `board.agent_track.lanes`.
- `web/src/components/Card.tsx` — status dot for `task.last_run` (queued gray / running pulsing amber /
  succeeded green / failed red).
- `web/src/components/CardDrawer.tsx` — "Agent runs" section: run list (status/lane/elapsed/cost/error),
  a "Run agent" button when the card's lane is an agent lane, "Open artifact" for a succeeded run.
- `web/src/components/ArtifactView.tsx` (new) — fetch `GET /api/artifacts`, render frontmatter as a
  compact header + body via `react-markdown` + `remark-gfm`, scrollable in the drawer.
- `web/src/styles.css` — `.run-chip` states + `.artifact-view` typography (reuse existing CSS vars; no
  new palette).
Follow docket web house rules (React Query is the only state layer; plain CSS with vars; no new state
libs; no syntax-highlighter). The Run button invalidates `["board"]` + `["runs", taskId]`. `ArtifactView`
must render the real claudster PRD shape (frontmatter + GFM tables/checklists).
Commit: `feat(docket): A4 render-back UI + oli.index.md`.

### Hard rules (unattended safety)
- Do NOT publish anything. Do NOT push to any remote, open PRs, or merge.
- Do NOT run a live `claude -p` / real agent. Test only via the existing `tests/fixtures/fake_claude.py`
  and unit/build tooling. The live drag→PRD recording (A4's human evidence) is OUT of scope — record it
  as human-required.
- Only touch the files listed above (+ their tests). Do not modify claudster. Do not refactor unrelated
  code. Do not ask questions; record unresolved items under "## Open questions".
- If a gate is red after ≤3 focused fix attempts, STOP and write the handoff.

### Validation gate (must be green)
1. `E:\Projects\docket\.venv\Scripts\python -m pytest tests/ -q` → all green (357 + new).
2. `cd web && npm install && npm run build` → succeeds (tsc + vite).
3. `cd web && npx vitest run` → green (add a vitest for the run-status chip mapping + the client's
   artifact-path encoding).
4. Determinism holds: `reduce(read_events()) == board.json` after the oli_index hook.
5. Opt-in safety still holds (enabled=false → zero agent.run.* + no oli.index churn on non-Ideas lanes).

### When you finish (or stop)
Append a "## A4 session (2026-07-04)" section to
E:\Projects\claudster-source\docs\analysis\IMPL-STATUS.md: what shipped, gate results, the human-required
A4 evidence (live drag→PRD recording, needs 1.3.15 + real claude), any "## Open questions". Then run the
mandatory branch/commit report (both repos) exactly as in
`.claudster/prompts/agentic-pipeline-impl.md`'s ADDENDUM and paste it verbatim into IMPL-STATUS.md and
the console.

Begin by reading ROADMAP §A4/§C7 + IMPL-STATUS, confirm the docket branch + baseline, then Task 1.
