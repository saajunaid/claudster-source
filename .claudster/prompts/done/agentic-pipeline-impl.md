# Autonomous implementation prompt — claudster×docket agentic pipeline

**What this is:** the complete, self-contained prompt for an unattended Claude Code session that
implements the first buildable slice of the agentic pipeline (Track 0 → A1 → A3 → A2). Paste the
"PROMPT" section below into a fresh session. The coding agent may also re-read this file mid-run for
its own reference.

**How to run:**
- Root the session at `E:\Projects\claudster-source`, then `/add-dir E:\Projects\docket` (A1/A2 write
  to docket, a separate repo — without this the run stalls on the first docket file).
- Model: **Opus 4.8** (A2's runner is concurrency + subprocess + Windows-kill code; unattended work
  rewards the more reliable model).
- Enable auto-accept edits (`--permission-mode acceptEdits` or the in-session toggle) so it doesn't
  pause. Safety comes from the branch-only + no-publish + no-live-`claude -p` rules below.
- Source of truth it builds from: `docs/analysis/DECISIONS.md` + `docs/analysis/ROADMAP.md`.

---

## PROMPT (paste everything below this line)

You are implementing the claudster×docket agentic-pipeline roadmap, AUTONOMOUSLY and unattended.
Work in two repos: E:\Projects\claudster-source and E:\Projects\docket (each is its own git repo,
each has its own .venv). Platform: Windows / PowerShell.

### Source of truth (read these FIRST, in full)
1. E:\Projects\claudster-source\docs\analysis\DECISIONS.md  — the locked decisions.
2. E:\Projects\claudster-source\docs\analysis\ROADMAP.md    — the build-ready PRD. Read §0 (mental
   model), §1 (pipeline), ALL of §C (normative contracts — copy schemas verbatim, never paraphrase),
   and the phase specs for Track 0, A1, A3, A2. Each phase has files, an implementation prompt,
   acceptance criteria, and a validation gate — follow them exactly.

### Scope — implement ONLY these, in this order. Nothing else.
1. Track 0 — publish safety (claudster)
2. A1     — agent.run.* events + reducer + run records (docket)
3. A3     — /prd headless-mode convention (claudster)  ← EDIT + TESTS ONLY (see hard rules)
4. A2     — agent-runner + harness adapter + lane trigger (docket)  ← CODE + fake_claude tests ONLY

OUT OF SCOPE — do NOT attempt: A4 and later; the S0 lavish spike; any web/React work; any Gemini/Track B
work. Stop after A2.

### Hard rules (unattended safety — non-negotiable)
- NEVER publish. Do not run `junai-push -Publish`, `junai-release`, `junai-publish-mcp`, `vsce`, twine,
  or any PyPI/marketplace upload. For Track 0, verify the -Publish gating by READING the code and running
  only `validate_pool.py` / `export_runtime_resources.py`. Do not execute `junai-push` at all (even
  without -Publish it pushes a mirror remote).
- NEVER run a live `claude -p` / real agent (no API keys assumed). For A2, test the runner ONLY via
  tests/fixtures/fake_claude.py per the phase spec. SKIP the B1/B2 live smoke tests — record them as
  human-required in the handoff.
- For A3: make the prd.md edit and run the claudster test suite + validate_pool, but SKIP the
  `junai-push -NoPublish` publish step and the live B2 smoke — record both as human-required.
- Do not push to any remote, do not open PRs, do not merge.
- Only touch files listed in each phase's file list (+ their tests). Do not refactor unrelated code.
- Do not ask questions. Make evidence-based decisions; record any unresolved item in the handoff under
  "## Open questions". Where the harness has AskUserQuestion, do not use it.

### Per-phase protocol
1. At the start, in EACH repo you'll touch, create a feature branch off the current branch:
   claudster → `feat/agentic-pipeline` ; docket → `feat/agentic-pipeline`. Commit only to these.
2. Confirm a GREEN baseline before starting a repo's first phase:
   - claudster: `python -m pytest scripts/tests/ claude-harness/hooks/tests/`  (expect 242 passed)
   - docket:    `E:\Projects\docket\.venv\Scripts\python -m pytest tests/ -q`   (expect all green)
   If baseline is red, STOP and report — do not build on a broken base.
3. Implement the phase exactly per its ROADMAP spec + the §C schemas. Where the phase says TDD
   (A1, A2), write the failing tests FIRST, then make them pass.
4. Run that phase's validation gate (the exact commands in the phase). It must be green.
5. If green → commit with a conventional message (e.g. `feat(docket): A1 agent.run.* events + reducer`).
   Then proceed to the next phase.
6. If a gate is red after at most 3 focused fix attempts → STOP, leave the tree as-is on the branch,
   and write the handoff describing exactly where and why.

### Global quality gate (must hold after every phase — see ROADMAP §Q)
- Determinism: `reduce(read_events()) == board.json` after any docket write path.
- Both suites green (the two baseline commands above, plus new tests).
- Layering: docket runner calls engine ops only; reducer stays pure; no writer touches events.jsonl
  outside engine._commit.
- Opt-in safety: with agent_track.enabled=false, a regression test drags across all lanes and asserts
  zero agent.run.* events.
- Windows-first: process-group spawn pattern; separator-tolerant path compares; no pytest-xdist.

### Config note (locked)
Full board lanes = ["Triage","Ideas","PRD","Plan","Implement","Validate","Ship","Done"]. Agent lanes =
PRD·Plan·Implement·Ship. `/implement` does NOT exist — do not configure it; Implement lane command is a
placeholder (__TBD_A8__) resolved later (A8, out of scope) and is never triggered in this scope. Use the
§C2 agent_track block verbatim.

### When you finish (or stop)
Write a handoff to E:\Projects\claudster-source\docs\analysis\IMPL-STATUS.md containing: phases
completed (with commit hashes, per repo/branch), the exact human-required gates left undone
(A3 publish → plugin 1.3.15; B1/B2 live smokes; anything else), any "## Open questions", and the precise
next command to resume. Also print this summary to the console.

### ADDENDUM — branch + commit reporting (do this as the very last step, ALWAYS)
Before finishing (whether you completed the scope or stopped early), run these in BOTH repos and paste
the raw output verbatim into IMPL-STATUS.md under a "## Branches & commits" section, AND print it to the
console:

    # in E:\Projects\claudster-source
    git branch --show-current
    git log --oneline main..HEAD          # every commit you added on this branch
    git status --short                    # anything uncommitted/left dirty

    # in E:\Projects\docket
    git -C E:\Projects\docket branch --show-current
    git -C E:\Projects\docket log --oneline <base>..HEAD    # <base> = the branch you forked from
    git -C E:\Projects\docket status --short

For each repo also record: the branch name, the base branch you forked from, the number of commits
added, and whether the working tree is clean. If you created no branch in a repo (e.g. you never got to
its phases), say so explicitly. This section is mandatory — a validator with zero prior context must be
able to find every branch and commit from IMPL-STATUS.md alone.

Begin by reading DECISIONS.md and ROADMAP.md, then confirm both baselines, then start Track 0.
