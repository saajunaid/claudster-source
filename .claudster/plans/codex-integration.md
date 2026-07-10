---
type: plan
status: draft
feature: codex-integration
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-10T00:00:00Z
Creating Model: claude-opus-4-8
---

# Codex integration — cross-vendor review, fallback harness, second docket engine

## Why (the value beyond cross-review)
1. **Cross-vendor review** — a different vendor's model has different blind spots; codex reviewing
   Claude's diff catches bugs a same-vendor reviewer misses.
2. **Quota resilience** — Claude session limits are real (two live PRD runs died on one on 2026-07-10).
   With a `CodexAdapter`, a docket board flips `agent_track.harness: "codex"` and the pipeline keeps moving.
3. **Full fallback driving** — the claudster **codex export target already exists**
   (`.github/runtime-targets.json`, name `codex`: skills → `.agents/skills/`, `AGENTS.md`,
   `.codex/config.toml.example`; a `dist/runtime-resources/codex` build is present). When Claude quota is
   exhausted entirely, drive codex directly with the SAME claudster conventions. Built, never live-tested.
4. **Cheap mechanical batch work** — bulk codemods/renames via `codex exec`, preserving Claude quota for
   judgment-heavy work.
5. *(Mostly N/A here: Codex cloud/web tasks are GitHub-integrated; our Gitea is out of scope.)*

## Current state (verified 2026-07-10)
- `codex-cli 0.137.0` is INSTALLED on `IEVXCOPPOC01` (`C:\Users\jshaik\AppData\Roaming\npm\codex`).
  **Not authenticated** until the OpenAI Pro subscription lands (`codex login`).
- claudster: full `codex` export target defined + a dist build; **zero live validation**.
- docket (`E:\Projects\docket`): `src/docket/harness.py` has `CodexAdapter(_UnbuiltAdapter)` — a stub that
  raises `NotImplementedError`. `_CMD_KEY` already maps `"codex": "codex_cmd"`; config default
  `codex_cmd: "codex"` exists. The Gemini adapter (same file) is the exact precedent to mirror, including
  its tests (`tests/test_runner.py` Track-B section) and fake CLI (`tests/fixtures/fake_gemini.py`).
- docket's gate seam: `agent_track.preflight_cmd` / `review_cmd` accept ANY executable (the A8 fakes prove
  it); a wrapper script can therefore put codex into the Implement pipeline's review gate with ZERO docket
  code changes.

## Prerequisite (HUMAN)
OpenAI Pro subscription active + `codex login` completed on this box. Verify with
`codex exec "say ok"` before starting Phase 2+. Phase 1 needs no auth.

## Phases

### Phase 1 — Probe the real CLI contract (no auth needed)
**Goal:** pin the exact headless flags before writing any code — do NOT trust remembered flags.
**Implement:** run `codex --help` and `codex exec --help`; record in a new
`docs/analysis/codex-cli-contract.md`: the non-interactive subcommand, working-dir flag, model flag,
approval/sandbox flags, JSON/last-message output options (look for `--json` and/or
`-o/--output-last-message <file>` — the last-message file, if present, is the preferred parse target),
and exit-code semantics. Every later phase cites this file.
**Exit gate:** the doc exists with verbatim `--help` excerpts.
**Commit:** `docs: codex CLI 0.137 headless contract (probed, not assumed)`

### Phase 2 — `/claudster:cross-review` skill + wrapper script (claudster repo)
**Goal:** on-demand cross-vendor review from inside any Claude session.
**Touches:** `.github/skills/coding/cross-review/SKILL.md` (new — mirror an existing skill's frontmatter,
e.g. `code-review`'s), `.github/tools/codex_review.py` (new), `scripts/tests/test_codex_review.py` (new).
**Implement:**
- `codex_review.py`: args `--range <git range>` (default working diff) `--cwd <repo>`; builds a review
  prompt (port the adversarial-review wording from docket `runner.py:_review_prompt` — correctness, tests,
  security, conventions, simplicity; blocking/should-fix/nit; END WITH `REVIEW: CLEAN` or `REVIEW: BLOCKING`);
  invokes codex per the Phase-1 contract (non-interactive, read-only sandbox if available); prints codex's
  final message; exits 0 on CLEAN, 1 on BLOCKING, 2 on any parse/spawn failure (fail-closed).
  If `codex` is not on PATH or not authenticated → exit 3 with a one-line actionable message.
- SKILL.md: when to use (after a phase is green, before commit; second opinion on a risky diff); how to run
  the tool; how to interpret exits; instruct the agent to FIX blocking findings or explicitly justify.
**TDD:** tests monkeypatch/shim the codex executable with a stub script (pattern:
docket `tests/test_runner.py:_launcher`) — assert prompt content carries the range, exit-code mapping
(CLEAN→0, BLOCKING→1, garbage→2, missing exe→3). No live codex in tests.
**Exit gate:** `python -m pytest scripts/tests/test_codex_review.py -q` pass; full suite + validate_pool OK.
**Commit:** `feat(skills): /claudster:cross-review — codex as a cross-vendor reviewer`

### Phase 3 — Validate the codex export bundle live (HUMAN-in-loop, cheap)
**Goal:** prove claudster-in-codex actually works.
**Implement:** `python export_runtime_resources.py` (codex target) → copy
`dist/runtime-resources/codex/*` into a scratch repo → `codex` interactive: confirm it reads `AGENTS.md`
(ask it "what conventions apply here?") and can execute one exported skill's workflow (e.g. ask for a
`code-review` of a small diff). Record findings + any export-target fixes in
`docs/analysis/IMPL-STATUS.md`. Fix mapping issues found (e.g. wrong skills dir for codex 0.137 — check
where `codex` looks for project skills per its docs/`--help`) in `runtime-targets.json` and re-export.
**Exit gate:** codex demonstrably uses the exported AGENTS.md + at least one skill; findings recorded.
**Commit:** `fix(export): codex bundle validated live (adjustments as found)`

### Phase 4 — `CodexAdapter` in docket (second pipeline harness)
**Repo:** `E:\Projects\docket` (branch `feat/codex-adapter` off `main`; NEVER push to main — it deploys).
**Goal:** `agent_track.harness: "codex"` drives the text lanes end-to-end, exactly like Gemini does.
**Touches:** `src/docket/harness.py`, `tests/fixtures/fake_codex.py` (new), `tests/test_runner.py`.
**Implement (mirror the Gemini work 1:1):**
- Replace the `CodexAdapter(_UnbuiltAdapter)` stub with a real adapter: `build_argv` per the Phase-1
  contract (non-interactive exec, auto-approval flag for file writes, model flag, prefer the
  last-message-to-file option if it exists — then `parse_result` reads THAT file; else parse stdout JSON);
  `prepare_env` strips `CLAUDECODE`; `parse_result` → `{is_error, cost_usd: None, num_turns: None,
  session_id}` (nullable per §C1 — success stays artifact-gated).
- If codex's final text lands in a file rather than stdout, ALSO extend docket
  `runner._extract_agent_text` only if needed — prefer making the adapter normalise to stdout-shaped
  output so the runner stays untouched.
- `fake_codex.py`: mirror `fake_gemini.py` — reads the prompt (runner-written `prompt.txt` fallback),
  writes the artifact named in the prompt's `"artifact":"…"` line, emits the codex-shaped envelope per the
  Phase-1 contract; modes `ok` / `no_artifact` / `error` via `FAKE_CODEX_MODE`.
- Tests: `test_codex_adapter_build_argv`, `test_codex_adapter_parse_result`,
  `test_codex_adapter_prepare_env_strips_claudecode`, `test_get_adapter_selects_codex`, and the
  end-to-end `test_codex_harness_drives_prd_run_end_to_end` (mirror
  `test_gemini_harness_drives_prd_run_end_to_end`, asserting `creation-agent: codex` in the artifact).
  Remove/replace `test_codex_adapter_is_still_a_stub`.
**Exit gate:** `uv run --extra dev pytest tests/test_runner.py -q` pass; full docket suite green (430+).
**Commit:** `feat(harness): CodexAdapter — codex as a second docket pipeline harness`

### Phase 5 (optional, after Pro is active) — codex as the Implement review gate
**Goal:** cross-vendor review INSIDE the A8 pipeline: `agent_track.review_cmd` → a wrapper.
**Implement:** `tools/codex_review_gate.py` in docket (or reuse claudster's `codex_review.py`): accept the
claude-style argv the runner passes (`-p <prompt> --output-format json …` — see `_spawn_phase`), extract
the prompt, run codex with it, emit a claude-shaped JSON envelope `{"is_error": false, "result": "<codex
text ending in REVIEW: CLEAN|BLOCKING>"}` on stdout. Config: `review_cmd` → a launcher for this script.
One integration test with a stubbed codex. Document in the docket README's agent section.
**Exit gate:** an Implement-lane run (fake implement + THIS gate with stubbed codex) completes with the
review verdict parsed. **Commit:** `feat(agents): codex wrapper for the Implement review gate`

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\codex-integration.md fully, then execute it
autonomously. Phases 1–3 run in E:\Projects\claudster-source; Phase 4–5 in E:\Projects\docket on branch
feat/codex-adapter (create from main; NEVER push docket main — pushing deploys prod). Rules: never trust
remembered codex flags — Phase 1's probed contract doc is the only source; never ask a question the plan,
the probed contract, or the Gemini precedent can answer; TDD; full suite after each phase (claudster:
python -m pytest -q --import-mode=importlib; docket: uv run --extra dev pytest -q); commit per phase, only
the files your phase touched; update this plan's phases with ✅ + hash. Phase 3 needs codex login (HUMAN) —
if not authenticated, do Phases 1, 2, 4 and mark 3/5 blocked-on-human. junai-push (bare) allowed after
claudster phases.
```
