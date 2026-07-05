# Independent validation — claudster × docket agentic pipeline (for Fable 5, fresh session)

**How to run:** fresh Claude Code session, **model Fable 5** (`/model fable`), root at
`E:\Projects\claudster-source`, then `/add-dir E:\Projects\docket`.

**Two hard rules:**
1. **Zero subscription quota — NO live `claude -p` / no agent spawns of any kind.** The test suites use
   FAKE stubs (`fake_claude`, `fake_lavish`), so re-running them spawns no real agent and costs nothing.
   Rigor comes from re-running those suites + static code review + small throwaway probe scripts (that
   never call `claude`). Do not attempt any `--plugin-dir`/live behavioural check.
2. **Change no source.** Don't edit/publish/push/merge any code, config, or test. The ONLY file you write
   is your report at the fixed path below. Throwaway probe scripts go in your scratchpad/temp dir only.

**Deliverable:** write your full report to
**`E:\Projects\claudster-source\docs\analysis\VALIDATION-REPORT-fable.md`** and, as your final line,
print `VALIDATION COMPLETE → docs/analysis/VALIDATION-REPORT-fable.md`.

---

## PROMPT (paste below this line)

You are an INDEPENDENT validator with fresh eyes. Two repos hold an in-progress feature built by another
agent over a long session: `E:\Projects\claudster-source` and `E:\Projects\docket`, both on branch
`feat/agentic-pipeline`. Verify the work against ground truth and find what's wrong — correctness,
robustness, security, and honesty of the reported status. **Do NOT trust the author's self-report**
(`docs/analysis/IMPL-STATUS.md`); treat its claims as hypotheses to disprove.

**Hard rules (repeat):** NO live `claude -p` or agent spawn — zero quota; the suites use fakes, so
running them is free. Change no source; write ONLY your report file; probe scripts in a temp dir only.

### What was built (scope to validate)
The idea→ship pipeline slice: a docket kanban whose lane moves trigger headless claudster agents.
- **claudster** (`git log --oneline main..HEAD`): Track 0 publish-safety (inverted `junai-push`, plugin-
  bundle validator), `/prd` + `/feature-plan` headless conventions (never-interview on terse input) +
  visual-companion HTML emit, a headless-convention lint test, plugin → 1.3.17.
- **docket** (`git log --oneline main..HEAD`): A1 `agent.run.*` events + reducer, A2 runner + harness
  adapter + lane trigger, A4 render-back UI + `oli.index.md`, cap-race fix, namespaced-command + Windows
  `shutil.which` fixes, A5 v1 visual-in-drawer (sandboxed iframe), A5 v2 Refine-in-Lavish (multi-turn).
- **Design docs** (not code): `docs/analysis/ROADMAP.md`, `DECISIONS.md`, `A8-MINI-PRD.md`.

### Method (do all of it — none of it spawns a live agent)
1. **Re-run every suite yourself and report the ACTUAL numbers** (don't quote IMPL-STATUS):
   - docket: `E:\Projects\docket\.venv\Scripts\python -m pytest tests/ -q`; then `cd web && npm run build`
     and `npx vitest run`.
   - claudster: `C:\Python\python.exe -m pytest scripts/tests claude-harness/hooks/tests -q` (the repo
     `.venv` lacks pytest — use `C:\Python`); then `python validate_pool.py` + `--profile claude`.
   Flag ANY discrepancy vs IMPL-STATUS.
2. **Review every commit diff** on both branches; check code matches the message and no commit swept in
   unrelated files.
3. **Adversarially probe the high-risk areas — statically, or with throwaway probe scripts (no claude).**
   For each, try to find the failure:
   - **Security — sandboxed visual iframe** (`docket web/src/components/VisualView.tsx` +
     `api._read_artifact`): is `sandbox=""` (no `allow-scripts`) sufficient for agent-generated HTML? Can
     the `/api/artifacts` guards be bypassed (path traversal, `..`, symlink, non-`.claudster/`, only
     `.md`/`.html`, 1 MiB cap)? Write a small pytest-style probe against `_read_artifact` to attempt a
     bypass (no agent needed).
   - **Runner robustness** (`docket src/docket/runner.py`): can a run ever stick in `running`? Is EVERY
     failure path routed to `fail_agent_run`? Is the cap check atomic (it lives in the serialized
     `queue_agent_run` — verify)? Is the Windows process-group kill correct? Does `shutil.which` handle a
     missing exe?
   - **Refine loop** (A5 v2): does the background thread block the run worker? Does every failure →
     `refine_failed`? Does the multi-turn loop always terminate (no infinite poll/revise)?
   - **Determinism & opt-in** (reducer): does `reduce(read_events()) == board.json` hold on the new
     paths? With `agent_track.enabled=false`, are there truly ZERO agent effects (find the test AND reason
     about gaps it misses)?
   - **The two live-caught fixes:** confirm the config + runner actually use `/claudster:*` namespaced
     commands and `shutil.which`; grep that nothing still hardcodes bare `/prd` or a bare `claude` exec.
   - **Layering:** does any writer touch `.docket/events.jsonl` outside `engine._commit`? Runner calls
     engine ops only?
   - **claudster headless conventions (STATIC only — no live run):** read the `## Headless mode` sections
     in `prd.md`/`feature-plan.md` and the lint test; judge whether the never-ask wording is genuinely
     strong enough to stop an interview on a bare title, purely by reading it. Do NOT run it live.
4. **Assess the A8 mini-PRD** (`docs/analysis/A8-MINI-PRD.md`): are the locked safety invariants
   (never-implement-on-default-branch, runner-runs-tests-itself, fail-if-untested, mandatory preflight +
   code-review gates) sufficient to make autonomous code-writing safe? Find any hole an autonomous
   implement could slip through.

### Report (write to docs/analysis/VALIDATION-REPORT-fable.md)
Structure it exactly so the author can parse it:
- `# Independent validation report (Fable 5) — <date>`
- `## Verdict` — one line per area (tests / correctness / robustness / security / status-honesty /
  A8-design): PASS | CONCERNS | FAIL.
- `## Test numbers (observed)` — the actual counts you ran, per suite.
- `## Findings` — a numbered list, MOST SEVERE FIRST. Each: severity, file:line, the concrete failure
  scenario, and a suggested fix. Empty only if you genuinely tried to break it and couldn't.
- `## Status-honesty check` — any IMPL-STATUS.md claim that does NOT match what you observed.
- `## A8 design assessment` — holes/risks in the locked safety invariants, or "sound".
- `## What I could NOT verify` — anything gated on a live run (headless behaviour, real E2E) that you
  correctly did not spend quota on; note it's author-claimed, not re-verified.
Be adversarial — a report that just agrees is worthless. End with the exact line:
`VALIDATION COMPLETE → docs/analysis/VALIDATION-REPORT-fable.md`
