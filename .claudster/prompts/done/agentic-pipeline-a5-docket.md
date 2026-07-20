# Prompt — A5 docket side: render the visual companion + opt-in "Refine in Lavish"

**Context / revised design (an investigation on 2026-07-04 changed §C8):** lavish does NOT embed cleanly
in docket — it opens its OWN browser window and its `poll` is a blocking loop, which fights the one-shot
headless runner. So A5 was re-shaped to **"visual-in-docket + opt-in decoupled refine"** (user-chosen):
- **Visual (done, claudster side, shipped in plugin 1.3.17):** the headless `/prd` and `/feature-plan`
  now ALSO write a self-contained `<slug>.html` visual companion next to the `<slug>.md`. Proven live —
  it produces a professional, scannable visual (Problem/Success cards, FR/NFR tables, inline
  `assumed`/`TECH-DECISION OPEN` tags). This session renders it in docket and adds the opt-in refine loop.

**How to run:** root at `E:\Projects\claudster-source`, `/add-dir E:\Projects\docket`; Opus 4.8;
auto-accept; continue on the existing docket `feat/agentic-pipeline` branch. Docket-only.

---

## PROMPT (paste below this line)

You are building the docket side of A5, continuing the existing `feat/agentic-pipeline` branch in
`E:\Projects\docket` (its own repo/.venv; Node for web). Docket-only. Do NOT publish, push, or open PRs.
Read `E:\Projects\claudster-source\docs\analysis\ROADMAP.md` §C5/§A4/§A5 + `IMPL-STATUS.md` (the A5 design
+ the "visual companion" finding) first. Baseline: `.venv\Scripts\python -m pytest tests/ -q` → 368.

### Task 1 — render the visual companion in the drawer (A5 v1; the main deliverable)
The headless run now writes `<artifact_dir>/<slug>.html` next to `<slug>.md` (plugin 1.3.17). Surface it:
- **Runner** (`src/docket/runner.py`): after `_validate_artifact` succeeds, check for a sibling
  `<artifact_dir>/<slug>.html`; if present, pass its repo-relative path to `complete_agent_run` as a new
  optional `visual_path`. Best-effort — a missing `.html` is NOT a failure (older plugins won't emit it).
- **Events/reducer** (`events.py`/`reducer.py`, spec §11): `agent.run.completed.data` gains optional
  `visual_path` (nullable); reducer copies it onto the run record. Keep determinism + old-log
  compatibility (missing key → None).
- **API** (`api.py`): extend `GET /api/artifacts` to also serve `.html` (currently `.md`-only) — same
  guards (relative path, resolved under repo root AND under `.claudster/`, size cap). Return the raw HTML
  for `.html` (the web renders it in a sandboxed iframe), the parsed `{frontmatter, body}` for `.md`.
- **Web** (`web/src/components/CardDrawer.tsx` + a new `VisualView.tsx`): when a succeeded run has a
  `visual_path`, show an **"Open visual"** control that renders the HTML in a **sandboxed iframe**
  (`<iframe sandbox srcdoc={html}>` or `src` to the artifacts endpoint — NO `allow-scripts`; the visual
  is inline-styled, no JS needed) in a slide-over/modal, with a "open in new tab" affordance. Agent-
  generated HTML MUST be sandboxed (no script execution) for safety.
- **Types/client** (`web/src/api/types.ts`, `client.ts`): `Run.visual_path?: string`; `getVisual(path,
  project?)` fetching the raw HTML.
- **Tests**: runner detects the sibling `.html` (extend `fake_claude.py` to also write one); reducer
  copies `visual_path`; API serves `.html` under the guards and rejects traversal/non-`.claudster` paths;
  vitest for the VisualView sandbox attributes.
Commit: `feat(docket): render the PRD/plan visual companion in the drawer (A5 v1)`.

### Task 2 — opt-in "Refine in Lavish" (A5 v2; decoupled; lavish opens its OWN window)
Design honestly around lavish's reality (it is a standalone surface, not an embed; `poll` blocks):
- A **"Refine in Lavish"** button in the drawer (shown when a run has a `visual_path`) POSTs a new
  refine run. Config: `agent_track` gains `refine_enabled` (default false) so this is opt-in.
- **Runner refine flow** (a new run kind, `agent.refine.*` events, or reuse `agent.run.*` with a
  `kind:"refine"`): start `npx -y lavish-axi <visual.html>` in the project (this opens lavish's OWN
  browser window on the user's screen — that is expected; do NOT try to iframe it), record the returned
  session URL on the run so the UI can show "Lavish is open — annotate there", then `npx -y lavish-axi
  poll <visual.html>` (long-poll; run stays `running`, surfaced as "awaiting your annotations"). On
  feedback, spawn `claude -p "/claudster:prd <original context> + the lavish annotations + revise"` to
  rewrite the `.md` + `.html`, then `lavish-axi end`. Timeout must be long (human-paced); make the poll
  cancellable from the UI (an "end refine" action → `lavish-axi end`).
- Windows notes: resolve `npx`/`lavish-axi` via `shutil.which` (same shim issue as `claude`); if port
  4387 is stuck, `taskkill` (lavish's own recovery is unix-only — document it).
- This phase is genuinely harder (long-lived run, external tool orchestration). If it gets fiddly,
  ship Task 1 alone (the visual render is the bulk of the A5 value) and leave Task 2 as a follow-up.
Commit: `feat(docket): opt-in Refine-in-Lavish loop (decoupled) (A5 v2)`.

### Gate + finish
`.venv\Scripts\python -m pytest tests/ -q` (368 + new) green; `cd web && npm run build && npx vitest run`
green; determinism + opt-in-off invisibility hold. Append an A5 section to
`E:\Projects\claudster-source\docs\analysis\IMPL-STATUS.md` (what shipped + the human evidence: a live
drag→PRD→"Open visual" recording) and run the branch/commit report addendum. Do NOT publish/push.

Begin with Task 1 (the visual render) — it's the main value and lower risk.
