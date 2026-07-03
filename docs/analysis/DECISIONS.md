# Decisions — claudster × docket integration (locked 2026-07-03)

Authoritative decision record from reconciling `pass1-foundations.md` + `pass2-integration.md`.
These answers are the input to the merged build roadmap. See `RECONCILE.md` for method.

## Hard requirement (overrides defaults)
**Non-Claude harness support is mandatory.** Claude Code is the local/dev harness; **Gemini CLI**
(and possibly Codex) must work for enterprise/COTS use. The harness must sit behind a **swappable
adapter** — switching = config change, not a rewrite. Nothing may hardcode `claude`.
Note: CLI harnesses (Claude Code, Gemini CLI, Codex) are spawnable by docket's runner; IDE-shaped
harnesses (Antigravity, Copilot) are a separate integration lane (they consume skills but can't be
spawned headlessly) — Antigravity's scriptability is an open research item.

## The seven decisions
1. **Runner home → Docket-owned runner.** The runner lives inside `docket serve` and spawns the
   harness CLI directly through a swappable adapter. Do NOT build Pass 1's `run_skill_headless` MCP
   trigger tool (not needed; no concrete non-docket trigger). MCP stays in-session only.
2. **Second harness → Gemini CLI, built and proven first** (after Claude works locally). Requires a
   new Gemini export target in claudster. The runner's spawn adapter is designed in from day one.
3. **Pipeline WIP → Accept WIP=1 per repo for now** (enforce in docket UI: refuse a 2nd in-flight
   card). **GRADUATION GOAL (recorded):** once the single-pipeline flow is proven, move claudster to
   **per-feature pipeline-state files** so multiple ideas run concurrently in one repo. Tracked
   milestone, not a dead end.
4. **Scheduling → Docket owns it** (cron inside `docket serve`). Portable across harnesses. Not
   Claude Code's native `/schedule` (Claude-locked).
5. **UI shape → One UI: a "command" view inside docket.** Reuse docket's React SPA. "ClaudsterOS"
   kept only as the view's title/branding. No separate app.
6. **Interview/visual transport → lavish-axi (harness-agnostic).** Roll in ALL of lavish's
   capabilities, not just interviews: **visual HTML prototyping of proposed changes + annotation +
   interview**. Adopt via `npx` (point-at, never vendor). Final wiring at the interview/visual phase.
   Rejected: Claude Agent SDK callback (Claude-only — conflicts with the hard requirement).
7. **docket packaging → Publish to PyPI** as its own package (first-ever publish). Fallback name
   `docket-board` if `docket` is taken (console command stays `docket`). **Also evaluate an `npx`
   launcher** for convenience — caveat: docket's runtime is Python, so npx would be a thin Node
   wrapper that still needs Python. Separate from claudster; coupled by versioned contract.

## Carried-over settled verdicts (from both passes, unchanged)
- claudster stays a **plugin** (not a standalone harness); Claude Code / Gemini CLI / Codex are the
  harnesses. MCP = in-session tool access, not the trigger.
- **Packaging: separate**, coupled by the `.claudster/*.md` file + frontmatter contract (spec §11).
- **Single event log** = docket's `events.jsonl`; one writer per fact.
- Smallest slice = **OLI→PRD** (drag card → headless `/prd` → PRD/prototype rendered in drawer, no
  auto-advance).
- Opt-in track, single-agent first, **ISD→deploy hard-gated** (3 layers).
- docket **never** builds a stage engine; reuse claudster's `transitions.py` via junai-mcp only when
  multi-stage autopilot lands.

## Fix-regardless items (independent of the integration)
- **Invert `junai-push` publish default** (currently auto-publishes to PyPI = permanent). Ship first.
- **Add a validator for the shipped plugin bundle** (currently zero validation).
- **Fix Dream Memory packaging** (scripts omitted from the bundle → layer is silently inert); then
  2-month sunset test via `/usage-review`.
- **OKF-lite** KB frontmatter; onboarding 9→3 steps with a `[harness]` config section.

## Lane names (locked 2026-07-04) — plain + concept-forward hybrid
**Triage → Ideas → PRD → Plan → Implement → Validate → Ship → Done.** Four agent lanes:
PRD·Plan·Implement·Ship (Validate = human). **Two-stage intake (decided):** Triage = raw unsorted
capture (docket auto-injects at index 0, `config.py:87`); Ideas = promoted OLIDs ready for a PRD;
`oli.index.md` indexes the Ideas lane. Lanes are config strings — any user renames. "OLID" stays the
term for a one-line idea card. Note: `/implement` does NOT exist — Implement lane driven by
`pipeline_runner.run_plan`/`fast_track_from_plan` or a `/tdd` loop (resolved in A8's mini-PRD).

## Full pipeline scope (confirmed — this is the destination, not OLI→PRD)
Lanes: **Ideas → PRD → Plan → Implement → Validate → Ship → Done**. Four agent lanes.
- First idea posted → generate read-only `.docket/oli.index.md` (human-readable index of all OLIDs;
  board.json remains the machine source of truth).
- PRD lane: headless skill runs `/prd` **with lavish interview** → `.claudster/prd/<slug>.md` → rendered
  in UI (markdown + lavish visual prototype).
- IPD lane: `/feature-plan` **with lavish interview** → `.claudster/plans/<slug>.md` → highlights in UI.
- IID lane: headless execution of the plan; **tests are built into the plan (no separate test lane)**.
- IID → IVD: **auto-advance** on implementation-complete (runner emits completion event).
- IVD: human validation; IVD → ISD: `/ship` deploy, **hard-gated (3 layers)**, per-project deploy target.
- **lavish is CORE and pulled forward** (not deferred): visual prototyping + annotation + interview at
  PRD and IPD. Adopt fully via npx.
- **Slice sequencing:** OLI→PRD ships first to prove runner+adapter+events+render. Target is the full
  interview UX in slice 1 (**option b**), **gated on the lavish Windows spike** — run the ~1hr spike
  first; if it passes, build lavish into slice 1; if flaky, ship headless-first (option a) and add
  lavish as an immediate fast-follow. Runner/adapter/`/prd`-headless-convention are identical either way.

## Open / research items still to resolve
- Antigravity headless/scriptable entry point (needed before promising the docket loop with it).
- PyPI name `docket` availability.
- `npx` launcher feasibility for docket (Python runtime caveat).
- B1/B2 smoke tests: `claude -p` (and later `gemini -p`) auth + skill-loading under a Windows service.
