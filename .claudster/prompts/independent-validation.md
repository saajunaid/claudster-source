# Independent validation — claudster × docket agentic pipeline (for Fable 5, fresh session)

**How to run:** fresh Claude Code session, **model Fable 5** (`/model fable`), root at
`E:\Projects\claudster-source`, then `/add-dir E:\Projects\docket`. Read-only audit — do NOT change code,
publish, push, or merge. This is an independent verification; you are the skeptic.

---

## PROMPT (paste below this line)

You are an INDEPENDENT validator with fresh eyes. Two repos hold an in-progress feature built by another
agent over a long session: `E:\Projects\claudster-source` and `E:\Projects\docket`, both on branch
`feat/agentic-pipeline`. Your job is to VERIFY the work against ground truth and find what's wrong —
correctness, robustness, security, and honesty of the reported status. **Do NOT trust the author's
self-report** (`docs/analysis/IMPL-STATUS.md`); treat its claims as hypotheses to disprove. Read-only:
change nothing, publish/push nothing.

### What was built (scope to validate)
The idea→ship pipeline slice: a docket kanban whose lane moves trigger headless claudster agents.
- **claudster** (`feat/agentic-pipeline`, `git log --oneline main..HEAD`): Track 0 publish-safety
  (inverted `junai-push`, plugin-bundle validator), `/prd` + `/feature-plan` headless conventions
  (never-interview on terse input) + visual-companion HTML emit, a headless-convention lint test,
  plugin bumped to 1.3.17.
- **docket** (`feat/agentic-pipeline`, `git log --oneline main..HEAD`): A1 `agent.run.*` events +
  reducer, A2 runner + harness adapter + lane trigger, A4 render-back UI + `oli.index.md`, cap-race fix,
  namespaced-command + Windows `shutil.which` fixes, A5 v1 visual-in-drawer (sandboxed iframe), A5 v2
  Refine-in-Lavish (multi-turn loop).
- **Design docs** (not code): `docs/analysis/ROADMAP.md`, `DECISIONS.md`, `A8-MINI-PRD.md`.

### Method (do all of it)
1. **Re-run every test suite yourself and report the ACTUAL numbers** (don't quote IMPL-STATUS):
   - docket: `E:\Projects\docket\.venv\Scripts\python -m pytest tests/ -q`; then `cd web && npm run build`
     and `npx vitest run`.
   - claudster: `C:\Python\python.exe -m pytest scripts/tests claude-harness/hooks/tests -q` (the repo
     `.venv` lacks pytest — use `C:\Python`); then `python validate_pool.py` + `--profile claude`.
   Flag ANY discrepancy between what you observe and what IMPL-STATUS claims.
2. **Review every commit diff** on both branches (`git log --oneline main..HEAD`, then read the diffs).
   Check the code does what the commit message says, and that no commit swept in unrelated files.
3. **Adversarially probe the high-risk areas** — for each, try to find the failure, don't just confirm:
   - **Security — the sandboxed visual iframe** (`docket web/src/components/VisualView.tsx` +
     `api._read_artifact`): is agent-generated HTML actually safe? Is `sandbox=""` sufficient (no
     `allow-scripts`)? Can the `/api/artifacts` guards be bypassed (path traversal, symlinks, non-
     `.claudster/`, `.md`/`.html` only, size cap)? Try crafting a bypass.
   - **Runner robustness** (`docket src/docket/runner.py`): can a run ever stick in `running`? Is EVERY
     failure path routed to `fail_agent_run`? Is the Windows process-group timeout-kill correct? Does the
     cap check hold under concurrency (it was moved into the serialized `queue_agent_run` — verify it's
     actually atomic)? Does `shutil.which` resolution handle a missing exe?
   - **Refine loop** (A5 v2): does the background thread ever block the run worker? Does every failure →
     `refine_failed` (no stuck `running`)? Does the multi-turn loop terminate (no infinite poll/revise)?
   - **Determinism & opt-in** (reducer): does `reduce(read_events()) == board.json` hold after the new
     event paths? With `agent_track.enabled=false`, are there truly ZERO `agent.run.*`/`agent.refine.*`
     effects (find the test AND reason about gaps it misses)?
   - **The two live-caught fixes:** namespaced `/claudster:*` commands and `shutil.which` — confirm the
     config + runner actually use them; confirm nothing else still hardcodes bare `/prd` or `claude`.
   - **Layering:** does any writer touch `.docket/events.jsonl` outside `engine._commit`? Does the runner
     call engine ops only?
   - **claudster headless conventions:** read the `## Headless mode` sections in `prd.md`/`feature-plan.md`
     — are the never-ask guarantees actually strong, or could the model still interview? (Optional: verify
     live via `claude -p --plugin-dir` on a renamed test plugin with a terse title, as the author did —
     only if you have a working `claude` login; note the cost.)
4. **Assess the A8 mini-PRD** (`docs/analysis/A8-MINI-PRD.md`) for design soundness: are the locked
   safety invariants (never-implement-on-default-branch, runner-runs-tests-itself, fail-if-untested,
   mandatory preflight + code-review gates) sufficient to make autonomous code-writing safe? Find any
   hole an autonomous implement could slip through.

### Output
- **Verdict per area** (tests / correctness / robustness / security / honesty-of-status / A8-design):
  PASS / CONCERNS / FAIL, each with evidence (cite file:line).
- **Findings list**, most-severe first: anything wrong, risky, or overstated that the author missed —
  with a concrete failure scenario for each.
- **Status honesty check:** list any claim in IMPL-STATUS.md that does NOT match what you observed.
- **Independent test numbers** (yours, not quoted).
- If you find nothing material, say so plainly — but only after genuinely trying to break it.
Be adversarial. A validation that just agrees is worthless.
