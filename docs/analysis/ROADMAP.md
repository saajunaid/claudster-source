# Merged Build Roadmap — Claudster × Docket (idea→ship agentic pipeline)

**Status:** build-ready. Reconciled from `pass1-foundations.md` + `pass2-integration.md`; decisions in
`DECISIONS.md`. **Date:** 2026-07-03.

**How to use:** §C holds the normative contracts (schemas written once — copy verbatim, never
paraphrase). Phases reference them by number. Each phase is independently shippable with a
self-contained implementation prompt, exact file paths, acceptance criteria, and a validation gate. A
Sonnet/Opus agent should implement a phase from its prompt + the referenced §C schemas alone.

**Path convention:** `claudster:<path>` = `E:\Projects\claudster-source\<path>`; `docket:<path>` =
`E:\Projects\docket\<path>`.

---

## 0. Mental model (hold this while building)

Three roles, three owners — nothing changes shape:
- **WHO runs agents → docket** (the runner, inside `docket serve`).
- **HOW agents execute → the harness** (`claude -p` / `gemini -p` / `codex exec`) behind a **swappable
  adapter** (§C1). This adapter is the load-bearing seam for the non-Claude requirement.
- **WHAT agents do → claudster** (skills, pipeline knowledge, `.claudster/` artifacts).

Four rules: (1) **files are the contract** (`.claudster/*.md` + frontmatter); (2) **one append-only log**
= docket's `events.jsonl`, one writer per fact; (3) **the board IS the command deck** (command center is
a docket view); (4) **opt-in, single-agent, human-gated** (deploy never fires from a drag).

**Harness-neutral success signal:** a run succeeds iff **the expected artifact exists AND its
frontmatter parses** — never an exit code. This is what makes the adapter swap trivial: Claude/Gemini/
Codex differ in argv and envelope, but "did the `.md` appear?" is identical for all three.

## 1. The full pipeline (destination — OLI→PRD is only slice 1)

| Lane | Stage | Skill (headless) | Artifact | Auto-advance | Confirm |
|---|---|---|---|---|---|
| Triage | — | — (raw capture, unsorted) | — | — | — |
| Ideas | intake | — (promoted OLID; card + `oli.index.md`) | `.docket/oli.index.md` | — | — |
| **PRD** | prd | `/prd` + lavish | `.claudster/prd/<slug>.md` | no (human review) | no |
| **Plan** | plan | `/feature-plan` + lavish | `.claudster/plans/<slug>.md` | no (human review) | no |
| **Implement** | implement (+tests) | `run_plan`/`fast_track_from_plan` or `/tdd` loop (**TBD — A8**) | code + tests + `.claudster/reviews/` | **→ Validate on complete** | no |
| **Validate** | validate | — (human) | — | no | no |
| **Ship** | ship | `/ship` | deploy | no | **YES (typed)** |
| Done | closed | — | — | — | — |

Tests are built into the plan (claudster TDD) — **no separate test lane**. Implement does implement+test;
Validate is human validation.

> **Lane naming (validated + locked 2026-07-04):** full `config.lanes` =
> **`["Triage", "Ideas", "PRD", "Plan", "Implement", "Validate", "Ship", "Done"]`** (config strings —
> any user renames). **Two-stage intake (decided):** `Triage` = raw unsorted capture (docket
> force-injects it at index 0, `docket:src/docket/config.py:87 _ensure_triage_lane`); `Ideas` = promoted
> OLIDs ready for a PRD. `oli.index.md` indexes the `Ideas` lane. `done_lane` = `Done` (matches).
> **`/implement` does not exist** in claudster — the Implement lane is driven by
> `pipeline_runner.run_plan` (`:1102`) / `fast_track_from_plan` (`:844`) or a headless `/tdd` loop,
> resolved in A8's mini-PRD. Do not configure `command: "/implement"`.

---

## C. Global contracts (normative)

### C1 — Harness adapter (NEW; the non-Claude seam)

`docket:src/docket/harness.py` (new). The runner never spawns a CLI directly — it goes through an
adapter selected by `config.agent_track.harness`.

```python
from typing import Protocol, Any

class HarnessAdapter(Protocol):
    name: str
    def build_argv(self, prompt: str, *, model: str | None, permission_mode: str,
                   max_turns: int) -> list[str]: ...
    def prepare_env(self, base_env: dict[str, str]) -> dict[str, str]: ...
    def parse_result(self, stdout: str, stderr: str, returncode: int) -> dict[str, Any]:
        """→ {is_error: bool, cost_usd: float|None, num_turns: int|None, session_id: str|None}.
        Non-Claude harnesses may return None for cost/turns/session — that is allowed."""

class ClaudeCodeAdapter:            # A2 builds this one
    name = "claude-code"
    # argv: [claude_cmd, "-p", prompt, "--output-format","json",
    #        "--permission-mode", pm, "--max-turns", str(mt)] + (["--model", model] if model else [])
    # env : delete "CLAUDECODE" from base_env (nested-spawn fix,
    #        proven in claudster:.github/skills/workflow/skill-creator/scripts/improve_description.py:30)
    # parse: json.loads(stdout) envelope → is_error, total_cost_usd, num_turns, session_id

class GeminiCLIAdapter:             # Track B builds this one
    name = "gemini"
    # argv: [gemini_cmd, "-p", prompt] + (["--model", model] if model else []) + non-interactive flag
    # env : as-is (Gemini uses GEMINI_API_KEY / GOOGLE_API_KEY — no CLAUDECODE concern)
    # parse: best-effort; is_error from returncode; cost/turns/session = None
    # NOTE: verify Gemini CLI's headless output/flags in Track B before coding (BLOCKER B-G1)

class CodexAdapter:                 # future
    name = "codex"
    # argv: [codex_cmd, "exec", prompt] + (["--model", model] if model else [])

ADAPTERS = {a.name: a for a in (ClaudeCodeAdapter(), GeminiCLIAdapter(), CodexAdapter())}
def get_adapter(cfg) -> HarnessAdapter:
    name = cfg["agent_track"]["harness"]
    if name not in ADAPTERS: raise InvalidOperation(f"unknown harness {name!r}")
    return ADAPTERS[name]
```

**Success (all adapters):** `not parse_result(...).is_error` AND expected artifact exists AND its
frontmatter parses (`type:`+`feature:`). Artifact-missing after a clean exit = **failure**.

### C2 — Config `agent_track` (in `docket:src/docket/config.py` `DEFAULT_CONFIG`)

```json
"agent_track": {
  "enabled": false,
  "harness": "claude-code",
  "claude_cmd": "claude", "gemini_cmd": "gemini", "codex_cmd": "codex",
  "max_concurrent_runs": 1,
  "run_timeout_seconds": 1800,
  "max_turns": 50,
  "permission_mode": "acceptEdits",
  "model": null,
  "lanes": {
    "PRD":       {"command": "/claudster:prd",          "artifact_dir": ".claudster/prd",   "auto_advance_to": null,       "requires_confirmation": false},
    "Plan":      {"command": "/claudster:feature-plan", "artifact_dir": ".claudster/plans", "auto_advance_to": null,       "requires_confirmation": false},
    "Implement": {"command": "__TBD_A8__",              "artifact_dir": null,               "auto_advance_to": "Validate", "requires_confirmation": false},
    "Ship":      {"command": "/claudster:ship",         "artifact_dir": null,               "auto_advance_to": null,       "requires_confirmation": true}
  }
}
```
> **Commands MUST be plugin-namespaced `/claudster:<cmd>` (validated live 2026-07-04, B2 smoke).** Bare
> `/prd` does NOT resolve in `claude -p` — it errors "Unknown command: /prd. Did you mean /pdf?" (collides
> with a built-in). Only `/claudster:prd` / `/claudster:feature-plan` / `/claudster:ship` resolve. The
> runner passes `command` straight into the prompt, so the config MUST carry the namespaced form for the
> claude-code harness. (Other harnesses will use their own command syntax via the adapter/config.)
> **`Implement.command` is a placeholder** — `/implement` does NOT exist in claudster. A8 decides the
> real driver: `pipeline_runner.run_plan`/`fast_track_from_plan` (invoked via the `junai` CLI, not a
> slash command) or a headless `/tdd` loop over the plan's phases. Do not ship `"__TBD_A8__"`.

`harness` ∈ {claude-code, gemini, codex}; only `claude-code` implemented until Track B. `enabled:false`
ships disabled — every diff must be behaviorally invisible when off (regression test, §Q). WIP cap =
`max_concurrent_runs: 1` (enforced in UI + engine; see Milestone M1 for the graduation to per-feature).

### C3 — Events + reducer + run workdir

Four new event types (extend the closed set in `docket:src/docket/events.py`; `actor="runner"`):

```jsonc
// agent.run.queued
{ "run_id":"run_01J…", "task_id":"DKT-7", "lane":"PRD", "command":"/prd",
  "project":"E:\\Projects\\myapp", "requires_confirmation":false }
// agent.run.started   { "run_id":"…", "task_id":"…" }
// agent.run.completed
{ "run_id":"…", "task_id":"…", "artifact_path":".claudster/prd/x.md",
  "highlights":{"summary":"≤280","open_questions":2}, "duration_seconds":312.4,
  "cost_usd":1.87, "num_turns":23, "session_id":"…" }   // last 4 nullable (non-Claude harnesses)
// agent.run.failed
{ "run_id":"…", "task_id":"…", "error":"…", "exit_code":1, "duration_seconds":1800.0 }
// (Phase A10) agent.run.confirmed { "run_id":"…", "confirmed_at":"…" }
```

Reducer (`docket:src/docket/reducer.py`): board gains top-level `"runs": {}`; tasks gain `agent_runs`
(list, `setdefault`) + `last_run`. Handlers per Pass 2 §2.0.3 (queued→record; started→running;
completed→succeeded+copy fields; failed→failed+error; confirmed→queued+confirmed_at). No-op on unknown
ids. Determinism: all times from event `ts`. **Reducer skips unknown types already**
(`reducer.py:277-280`) — this is the forward-compatible extension point.

Run workdir `docket:.docket/runs/<run_id>/` (git-ignored): `prompt.txt`, `result.json` (verbatim
envelope), `stderr.txt`. Event payloads carry only refs/derived fields (blobs out of the log).

### C4 — Headless invocation prompt template (adapter builds argv; template is harness-neutral)

`cwd` = `run.project` (task's `project` or the board repo). `slug = engine._slugify(task["title"])`.
Timeout → Windows `CTRL_BREAK_EVENT` + 5s grace + kill (copy `claudster:.github/tools/mcp-server/
server.py:833-861`).

**Executable resolution (Windows — validated live 2026-07-04):** resolve the command via
`shutil.which(cmd) or cmd` BEFORE building argv. Bare `claude` is a `.CMD` shim (`…\npm\claude.CMD`) and
`subprocess.Popen` does NO PATHEXT resolution → `FileNotFoundError [WinError 2]`. Applies to every
harness's executable (`gemini`/`codex` too). Verified: once resolved + the command namespaced
(`/claudster:prd`), the full E2E goes queued→started→completed with artifact + `docket_id` merge.

````
{command} {title}

Docket card {task_id} — context:
Title: {title}
Description:
{description}

HEADLESS RUN RULES (mandatory):
- Non-interactive. No user present. Do not ask questions / use AskUserQuestion / pause for approval.
- Derive everything from the context and codebase; unresolved items go under "## Open questions".
- Write the artifact to {artifact_dir}/{slug}.md with standard frontmatter, feature: {slug}.
- End with exactly one fenced json block:
  ```json
  {"artifact":"{artifact_dir}/{slug}.md","summary":"<=280 chars","open_questions":<int>}
  ```
````
Highlights = last fenced `json` block in the result (fail-soft to `null`; artifact-existence is the real
success signal, not this block). When lavish is active (§C8) the "do not ask" rule is replaced by the
lavish interview loop for the interview-bearing lanes (PRD/IPD).

### C5 — HTTP API (under `/api`, existing auth posture)

```
POST /api/tasks/{task_id}/run     {"lane":"PRD"?}  → run record; 400 lane not in agent_track/disabled; 409 over cap
GET  /api/runs?task_id=&status=                    → [run records] newest first
GET  /api/runs/{run_id}                            → run record; 404
GET  /api/artifacts?path=<rel>&project=<name>?     → {path, frontmatter, body}
     guards: path relative; resolved under repo root AND under .claudster/; .md only; ≤1 MiB; 404 if absent
POST /api/runs/{run_id}/confirm   {"confirm_text":"DKT-7"}  (A10) → releases awaiting_confirmation iff == task_id
```
`GET /api/board` decorated (API layer, not stored) with `agent_track: {enabled, lanes:{<lane>:{command,
requires_confirmation}}}` so the UI badges agent lanes without a second request.

### C6 — Artifact/frontmatter contract (seam 1 — already live)

claudster emits (`claudster:claude-harness/commands/prd.md:24-33`, `feature-plan.md:52-60`): `type:
prd|plan`, `status: draft|current|done|superseded`, `feature: <slug>`, `creation-agent: claudster` +
authorship keys. docket manages exactly one key in plans, `docket_id`, via surgical non-destructive
merge (`docket:src/docket/projection.py:106-135`) and maps `status:`→lane via `status_lane_map`.
**Golden fixture** `docket:tests/fixtures/claudster_prd_frontmatter.md` (verbatim block) + a
`parse_frontmatter` test = the skill-drift tripwire.

### C7 — `oli.index.md` projection (NEW)

`docket:src/docket/oli_index.py` (new): `project_oli_index(repo_path, board) -> None` writes a read-only
`.docket/oli.index.md` — a markdown table of every non-archived card in the OLI/Inbox lane:
`| ID | Title | Lane | Created |`. Called best-effort from `engine._commit` after any event touching an
idea-lane card (never raises; mirrors `board.json` write discipline). Header notes "generated — do not
edit; source of truth is events.jsonl". board.json stays the machine source of truth.

### C8 — lavish integration (visual + annotation + interview; CORE, spike-gated)

lavish-axi adopted via `npx` (never vendored). Used at **PRD and IPD** lanes for: (a) **visual
prototype** — the skill emits an HTML artifact of the proposed PRD/plan using the project design system;
(b) **annotation + interview** — `npx lavish-axi <file.html>` opens the browser UI, `poll` blocks for
human feedback, `--agent-reply` answers. Contract:
- claudster side: a `lavish` extras skill (§Track C) instructing the agent to emit the HTML artifact and
  drive the poll loop; the PRD/IPD headless prompt, when `agent_track.lanes[L].interview: true`, replaces
  "do not ask" with "produce an HTML prototype at `.docket/runs/<run_id>/prototype.html`, open it via
  lavish, and incorporate annotations before finalizing the artifact".
- docket side: the render-back UI embeds the lavish session URL (iframe) in the card drawer so the human
  annotates **inside docket**; the run stays `running` until lavish `poll` returns `ended`.
- **Gated on Spike S0** (lavish Windows viability). If S0 fails, PRD/IPD ship headless-only (no
  interview) and lavish lands once the Windows path is resolved.

---

## S0 — Lavish Windows spike (FRONT-LOAD; ~1 hour; decides slice-1 shape)

Manual, on the target Windows box. `npx -y lavish-axi <sample.html>` → browser opens → annotate → `poll`
returns the annotation (TOON) → `end` closes; then kill the server mid-session and confirm recovery.
Record PASS/FAIL + notes in `docs/analysis/lavish-windows-spike.md`.
- **PASS →** build lavish into slice 1 (option b): PRD lane ships with the interview.
- **FAIL →** slice 1 is headless-only (option a); lavish becomes a fast-follow once patched/WSL-routed.
Runner + adapter + `/prd` headless convention are identical either way — start Track 0/A immediately in
parallel; S0 only gates when the interview is wired (A5).

---

## Track 0 — Publish safety (claudster; do FIRST, protects everything)

**Goal:** make an accidental permanent PyPI publish impossible; give the shipped plugin its first
validator. (Pass 1 Phase 0.)

**Files:** `claudster:sync.ps1` (auto-release `:1360-1388`; release `:1680-1810`), `claudster:
validate_pool.py` (profile allowlist `:1067-1071`), `claudster:README.md` `## Publishing`.

**Changes:** (1) invert default — `junai-push` never releases unless `-Publish`; `-NoPublish` = silent
deprecated no-op. (2) content-diff gate inside `junai-release` (SHA-compare server.py vs mirror; skip
unchanged). (3) `validate_pool.py --profile claude`/`claude-extras`: plugin.json shape+version match;
flattened SKILL.md frontmatter + roster count; commands/agents/hooks present; hooks.json references
resolve; leak scan; **assert `scripts/` contains every file the hooks import** (catches the Dream Memory
bug). (4) README update.

**Implementation prompt:** *In `E:\Projects\claudster-source`: edit `sync.ps1` so `junai-push`
auto-invokes `junai-release` only when a new `-Publish` switch is set (accept `-NoPublish` as a silent
no-op); add SHA256 content-diff gates before the MCP twine upload and `vsce publish` in `junai-release`;
extend `validate_pool.py`'s profile allowlist (`:1067-1071`) with `claude`/`claude-extras` implementing
checks (a)-(f) above against `dist/runtime-resources/claude/plugin{,-extras}/`; update README
`## Publishing`. Run the gate.*

**Gate:** `pytest scripts/tests/ claude-harness/hooks/tests/` → 242; `python export_runtime_resources.py`
→ 0; `python validate_pool.py [--profile claude|claude-extras]` → OK; manual: `junai-push` (keys present)
ends with no publish lines. **Evidence:** command transcript.

---

## Track A — The pipeline (lane by lane)

### A1 — Run events + reducer + records (docket) [Pass 2 P1]

**Goal:** the board represents runs (queued→running→succeeded/failed) purely as events, replay invariant
intact, before any process spawns.
**Files:** `docket:src/docket/events.py` (+4 types), `ids.py` (`new_run_id()` → `run_<ulid>`),
`reducer.py` (`runs` map + 4 handlers per §C3), `engine.py` (4 `_serialized` `_commit` wrappers:
`queue/start/complete/fail_agent_run`), `docket-build-spec.md` (§11 = §C2/§C3 verbatim), tests
(`test_events/reducer/engine`), `.gitignore` (`.docket/runs/`).
**Implementation prompt:** *In `E:\Projects\docket`, add agent-run lifecycle to the event core. Read
`events.py`, `reducer.py`, `engine.py` (`_commit`:141, `_serialized`:109), `ids.py`, spec §§2–5. Add the
four types + reducer handlers + engine ops exactly per §C2/§C3 of `docs/analysis/ROADMAP.md`
(copy the §11 block into `docket-build-spec.md`). TDD: failing tests first (each handler; unknown-id
no-op; determinism; full queue→start→complete replay equals board.json; fail path). Reducer stays pure;
no subprocess code. Gitignore `.docket/runs/`.*
**Gate:** `docket:.venv\Scripts\python -m pytest tests/ -q` green; delete board.json in a fixture repo,
`get_board`, assert equality.

### A2 — Agent-runner + harness adapter + lane trigger (docket) [Pass 2 P2 + §C1]

**Goal:** a lane move (or CLI) spawns a headless session **through the adapter** and translates the
outcome into A1 events. Ships the `ClaudeCodeAdapter`.
**Files:** `docket:src/docket/harness.py` (§C1; ClaudeCodeAdapter fully, Gemini/Codex stubs),
`docket:src/docket/runner.py` (~250 lines: `Runner` daemon worker, `enqueue`, `_execute` using
`get_adapter(cfg)` for argv/env/parse, artifact detection + frontmatter parse + post-hoc `docket_id`
merge), `engine.py` (`_maybe_enqueue_agent_run` best-effort after `_project_lane_change` in `move_task`),
`config.py` (§C2 block + `_ensure_agent_track` migration), `api.py` (§C5 endpoints + board decoration +
start runner in lifespan), `cli.py` (`docket run <task-id>` synchronous path),
`tests/test_runner.py`, `tests/fixtures/fake_claude.py` (stub exe; `FAKE_CLAUDE_MODE=ok|no_artifact|
hang|error`).
**Implementation prompt:** *In `E:\Projects\docket`, build the runner + harness adapter. Prereq: A1.
Read `engine.py` (locks:89-117, `move_task`:387-400, `_project_lane_change`:403-437), `config.py`,
`api.py`, `cli.py`, and §C1/§C2/§C4/§C5 of `docs/analysis/ROADMAP.md` (normative). Implement
`harness.py` with the `HarnessAdapter` protocol, a fully-working `ClaudeCodeAdapter`, and Gemini/Codex
stubs raising NotImplementedError. Implement `runner.py`: single daemon worker, `max_concurrent_runs`
respected, EVERY failure path → `fail_agent_run`, calls engine ops only (never `store.append_event`
directly) so the per-repo lock holds; `_execute` gets argv/env/parse from `get_adapter(cfg)` and uses
artifact-existence + frontmatter as the success signal. Wire the lane trigger into `move_task`
best-effort (never breaks a move). Add §C5 endpoints WITH the path-traversal guards (test them) + `docket
run` CLI. Tests via `fake_claude.py` (point `claude_cmd` at it): happy path (queued→running→succeeded,
artifact linked, docket_id merged, highlights parsed); no_artifact→failed; hang→timeout-kill→failed;
error→failed; unconfigured lane→400/InvalidOperation; over-cap→409; artifact endpoint rejects
`..`/absolute/non-.md/outside-.claudster. Board invariant holds after every scenario.*
**Gate:** `pytest tests/ -q` green. **BLOCKER smokes (must pass to close phase):** B1 auth under Windows
service context (`claude -p "Say OK" --output-format json` non-interactive w/ `ANTHROPIC_API_KEY`); B2
plugin+slash-command loading in `-p` (`claude -p "/prd smoke" --output-format json` produces the
artifact). End-to-end: `docket run DKT-<n>` on a real repo → `succeeded`.

### A3 — `/prd` headless convention (claudster) [Pass 1 P2 / Pass 2 P3]

**Goal:** `/prd` behaves headless (no interview, deterministic path, highlights block) — the substrate
lavish sits on.
**Files:** `claudster:claude-harness/commands/prd.md` (+`## Headless mode` section after the discovery
interview), publish `junai-push -NoPublish` → plugin **1.3.15**.
**Implementation prompt:** *In `E:\Projects\claudster-source`, edit only `claude-harness/commands/prd.md`.
After the Discovery section add `## Headless mode`: marker `HEADLESS RUN RULES` ⇒ no interview, no
AskUserQuestion, derive-don't-ask, unresolved → `## Open questions`, honor caller output path + `feature:`
slug, end with the single fenced json highlights block. Don't change the interactive flow or frontmatter.
Run `pytest scripts/tests claude-harness/hooks/tests -q` + `validate_pool.py`. Publish `junai-push
-NoPublish`; verify plugin 1.3.15 in the mirror.*
**Gate:** claudster suite green; `validate_pool.py` OK; B2 re-run shows zero interview turns; plugin 1.3.15
in mirror. (Parallel with A1/A2.)

### A4 — Render-back UI + `oli.index.md` (docket web + engine) [Pass 2 P4 + §C7]

**Goal:** the human sees everything from the board: OLID index, agent-lane badge, run status, rendered
PRD. **← OLI→PRD slice complete after this phase (headless).**
**Files:** `docket:src/docket/oli_index.py` (§C7) + hook into `engine._commit`;
`docket:web/package.json` (+`react-markdown`,`remark-gfm`); `web/src/api/types.ts` (Run/Board/Task
additions), `client.ts` (`runTask`/`getRuns`/`getRun`/`getArtifact`), `hooks/useRuns.ts`, `useBoard.ts`
(conditional 2s `refetchInterval` while any run queued/running), `components/Lane.tsx` (⚡ pill),
`Card.tsx` (status dot), `CardDrawer.tsx` ("Agent runs" section + Run button + Open artifact),
`ArtifactView.tsx` (new; fetch + react-markdown), `styles.css`.
**Implementation prompt:** *In `E:\Projects\docket`: (1) add `src/docket/oli_index.py` per §C7 and call it
best-effort from `engine._commit` on idea-lane events. (2) In `web/`, add run visibility + artifact
rendering per the file list; follow house rules (React Query only; plain CSS vars; no new state libs).
Run button calls `runTask` + invalidates `["board"]`+`["runs",taskId]`; `useBoard` polls 2s only while a
run is active. `ArtifactView` renders claudster PRD shape (frontmatter header + GFM body). `npm run
build` passes; vitest for the status-chip mapping + artifact-path encoding.*
**Gate:** `npm run build` + `npx vitest run` green; `pytest tests/ -q` green. **Slice evidence:** screen
recording of drag→PRD lane→pulsing→green chip+cost→rendered PRD in drawer, and `.docket/oli.index.md`
generated.

### A5 — lavish (visual prototype + annotation + interview) [SPIKE-GATED by S0]

**Goal:** PRD/IPD lanes gain the in-UI interview + visual prototype. If S0 FAILED, defer this phase and
proceed headless-only.
**Files:** claudster: `.github/skills/productivity/lavish/SKILL.md` (extras; §C8) + roster entry in
`runtime-targets.json`; `commands/prd.md` (+ conditional lavish branch); docket:
`config.py` (`lanes[L].interview: true`), `runner.py` (interview branch: keep run `running` until lavish
`poll` returns `ended`), `web/src/components/CardDrawer.tsx` (embed lavish session iframe).
**Implementation prompt:** *Implement §C8. In claudster add the `lavish` extras skill (invoke via `npx -y
lavish-axi`; visual HTML prototype + annotation poll loop) and a conditional branch in `prd.md`: when the
invocation sets interview mode, produce `.docket/runs/<run_id>/prototype.html` using the project design
system, open via lavish, incorporate annotations, then write the PRD. In docket, add `interview` per-lane
config, keep the run in `running` while polling, and embed the lavish session URL in the drawer. Test the
runner's interview branch with a fake lavish (stub `poll` returning immediate `ended`).*
**Gate:** with `interview:true`, a PRD run opens a lavish session and finalizes the PRD after annotation;
with `interview:false`, behaves as A3/A4. **Evidence:** recording of the annotate-in-docket loop.

### A6 — Command-center view (docket web) [Pass 2 P5]

**Goal:** one `"command"` view answering "what ran / queued / running / needs me", operations-room styled.
**Files:** `web/src/components/Sidebar.tsx` (+`"command"`), `App.tsx` (branch),
`CommandCenter.tsx` (new: Active / Queue / History / KPI tiles / Artifacts / Needs-attention — reuse
`Insights.tsx` Panel + `lib/boardStats.ts`), `styles.css` (`.command`-scoped worldmonitor tokens:
`#0a0a0a/#141414/#1e1e1e`, `#2a2a2a` borders, 4px radii/gaps, 12px `'Cascadia Code',Consolas,monospace`,
9–11px uppercase muted headers, semantic `#ff4444/#ffaa00/#44aa44/#3388ff`, tabular-nums); docket MCP
`run_agent`/`get_runs`/`get_run` tools (`mcp_server.py`, ≤2-sentence descriptions).
**Gate:** `npm run build`+vitest green; `pytest tests/ -q` green; MCP `run_agent` enqueues == API path.
**Evidence:** dark command view + light board screenshots; MCP tool-call transcript.

### A7 — Plan lane: `/feature-plan` headless + lavish [Pass 2 P6 part]

**Goal:** second agent lane proves generalization; plan rendered + highlights.
**Files:** `claudster:claude-harness/commands/feature-plan.md` (+`## Headless mode` + lavish branch) →
plugin **1.3.16**; docket config example adds the Plan lane (§C2 already lists it); reuse A2 runner + A4/A5
UI unchanged.
**Gate:** Plan-lane drag → `.claudster/plans/<slug>.md` with highlights in drawer; both suites green.
**Evidence:** recording PRD→Plan.

### A8 — Implement lane: headless implementation execution (both) [the big one — highest risk]

**Goal:** an Implement-lane drag executes the plan headlessly (implement + tests baked into the plan),
producing code + review artifact.
**Design:** ⚠️ **`/implement` does NOT exist** (validated). The Implement run must drive one of:
`pipeline_runner.run_plan` (`pipeline_runner.py:1102`) / `fast_track_from_plan` (`:844`) via the `junai`
CLI, OR a headless loop over `/tdd` (`claude-harness/commands/tdd.md`) per plan phase. Reads
`.claudster/plans/<slug>.md` and executes its phases. Deciding the driver is the FIRST task of this
phase's mini-PRD. Long-running:
raise `max_turns`/`run_timeout_seconds` per-lane; success signal = tests green + a `.claudster/reviews/
<slug>.md` (or the plan's `## Tracker` all-checked) rather than a single artifact file. **This phase
likely decomposes** — treat as its own mini-PRD when reached; flagged sub-decisions: per-phase
checkpointing, partial-failure handling, and whether IID auto-runs the code-reviewer agent before IVD.
**Files:** claudster: a headless implement entry (new/confirm existing); docket: runner support for
non-`.md`-artifact success (tests-green + review-file signal), longer timeouts, streaming progress to the
run record.
**Gate:** a small real plan executes end-to-end, tests pass, review artifact written, run → succeeded.
**Evidence:** recording of IID execution on a toy plan. **Do not start before A7 is proven in daily use.**

### A9 — Auto-advance Implement→Validate + Validate step

**Goal:** on Implement completion the runner moves the card to Validate (via `auto_advance_to`, one
`engine.move_task` call); Validate is human validation (no agent).
**Files:** `docket:src/docket/runner.py` (fire `auto_advance_to` on `complete_agent_run`, single-fire,
never into an agent lane that would re-trigger); UI shows "awaiting your validation".
**Gate:** Implement success moves card to Validate exactly once; no run triggered in Validate.
**Evidence:** recording.

### A10 — Ship deploy hard-gate (both) [Pass 2 P6 deploy part]

**Goal:** Validate→Ship runs `/ship` to deploy, gated by three independent layers.
**Design:** (1) `requires_confirmation:true` ⇒ `queue_agent_run` writes `awaiting_confirmation`; UI queue
shows a confirm box requiring the **task id typed exactly** (`POST /api/runs/{id}/confirm` → `agent.run.
confirmed`); (2) the worker refuses to spawn any confirmation-required run without `confirmed_at`
(defense-in-depth); (3) `/ship`'s own preflight/CI/health gates remain. `artifact_dir:null` ⇒ ISD success
= `/ship`'s structured report in `result.json`; highlights carry the deploy SHA.
**Files:** `docket:runner.py`/`api.py`/`reducer.py` (confirmed event) + `web` confirm UI;
`claudster:claude-harness/commands/ship.md` (headless section, per-project deploy auto-detect already
exists).
**Gate:** an ISD drag **cannot** start a run (test + manual); a typed confirmation releases exactly one.
**Evidence:** confirm-flow recording.

---

## Track B — Gemini CLI adapter (proves the switch) [decision #2]

**Goal:** `agent_track.harness: "gemini"` runs the whole pipeline via `gemini -p`. Requires (i) the
`GeminiCLIAdapter` (§C1) and (ii) a claudster **Gemini export target** so the skills load in Gemini.
**Files:** docket: `harness.py` `GeminiCLIAdapter` (real argv/env/parse); claudster:
`runtime-targets.json` new `gemini` target (`.gemini/skills/`, GEMINI.md, commands md→TOML via the
dormant `transforms` machinery, `settings.json` MCP snippet), `validate_pool.py --profile gemini`.
**BLOCKER B-G1:** verify Gemini CLI's headless flags/output format + `gemini -p` auth under a Windows
service (the Gemini analogue of B1/B2) before coding the adapter.
**Gate:** the OLI→PRD slice runs green end-to-end with `harness: "gemini"` on a repo with the Gemini
target installed; artifact + frontmatter identical to the Claude path (proves harness-neutral success).
**Evidence:** side-by-side PRD produced by both harnesses. **Sequence:** after A4 (the slice works on
Claude); can run parallel with A6+.

---

## Track C — Claudster hardening (parallel, non-blocking) [Pass 1 B/G + E]

Independent of the integration; schedule opportunistically.
- **C-1 OKF-lite KB frontmatter** (Pass 1 Phase 4): add `type`-required OKF frontmatter to KB notes +
  mandate in `kb.md`/`knowledge-transfer.md`; harden `extract_docmap_entries` to skip a leading `---`
  block; +2 checker tests. Gate: `check_doc_coverage.py --check/--reindex` exit 0; 60 tests.
- **C-2 Onboarding 9→3 + `[harness]` config** (Pass 1 Phase 3): `detect_harnesses()` via `shutil.which`;
  write a real minimal `.claudster/config.toml` `[harness]` section (`primary`/`model_routing`/
  `gateway_url`; reserve `[pipeline]`); one persona-filtered summary; `--harness` override; update the
  config test (real config now written). Gate: fresh temp project one-command; idempotent re-run.
- **C-3 Dream Memory packaging fix** (Pass 1 E/B.2): add `dream_memory.py`/`dream_capture.py`/
  `claudster_config.py` to the claude target `copies` in `runtime-targets.json` (Track 0's validator
  check (f) then locks it). **Then set a 2-month sunset test** — retire the layer if `/usage-review`
  shows no surfaced-fact influence by ~2026-09.
- **C-4 (already in Track 0):** the plugin-bundle validator.

---

## Milestone M1 — WIP=1 → per-feature pipeline state (recorded; post-proof)

**Trigger:** once the single-pipeline OLID flow is proven in daily use. **Change:** claudster's
`pipeline_init` is single-active-pipeline-per-repo (`server.py:687-710`) → move to **per-feature
state files** (e.g. `.github/pipeline-state.<feature>.json`) so multiple ideas run concurrently. Docket
lifts the UI WIP=1 guard accordingly. This is a claudster change (Pass 1 territory) — do NOT build
speculatively; it's a tracked graduation, not v1.

---

## Dependency graph

```
Track 0 ──────────────► (protects all publishes)
S0 (spike) ───────────► gates A5 only
A1 ─► A2 ─► A4 ──[OLI→PRD slice]──► A6 ─► A7 ─► A8 ─► A9 ─► A10
      A3 ┘ (parallel; needed by A2's B2 smoke)
      A5 (after A4, if S0 passed)
A4 ─► Track B (Gemini) ── parallel with A6+
Track C ── fully parallel, non-blocking
M1 ── after A8/A9 proven
```

## BLOCKER assumptions

| # | Assumption | Verify at | Fallback |
|---|---|---|---|
| B1 | `claude -p` auth in a non-interactive Windows service | A2 gate | run `docket serve` as user-session autostart (not NSSM) for v1 |
| B2 | slash-command + plugin discovery in `-p` (docs say yes) | A2 gate | `--plugin-dir`; worst case inline the skill body |
| B-G1 | Gemini CLI headless flags/output + service auth | Track B | Codex first, or keep Claude-only until resolved |
| S0 | lavish-axi runs on Windows | S0 (front-load) | headless-only slice; lavish fast-follow |
| B5 | PyPI name `docket` free | before docket publish | `docket-board` (console stays `docket`) |
| M1 | single-pipeline-per-repo acceptable for v1 | — (decided) | M1 graduation |

## Global quality gate (every phase, before any publish)

1. Determinism: `reduce(read_events()) == board.json` after every write path.
2. Both suites green: `docket: .venv\Scripts\python -m pytest tests/ -q`; `claudster: pytest scripts/tests
   claude-harness/hooks/tests -q` (242 baseline) + `validate_pool.py`.
3. Layering: runner→engine ops only; reducer pure; API/MCP thin; no writer touches `events.jsonl` outside
   `engine._commit`.
4. Opt-in safety: with `agent_track.enabled:false`, a regression test drags across all lanes and asserts
   zero `agent.run.*` events.
5. Windows-first: process-group spawn everywhere; separator-tolerant path compares; no pytest-xdist.
6. Harness-neutral: success = artifact-exists + frontmatter parse (never exit code); cost/turns may be null
   for non-Claude harnesses.
7. No blind trust: highlights best-effort; costs surfaced in UI; contract changes bump spec §11.

## Publish/rollback notes

- claudster: plugin versions auto-bump in `runtime-targets.json` on content diff; `junai-mcp` version in
  the **mirror** `pyproject.toml`; publish only at phase boundaries after the gate (**PyPI is permanent**).
- docket: `docket` 0.1.0 → 0.2.x per phase group; first PyPI publish before external adoption.
- Every phase is plain git-revertible; the only one-way door is each PyPI upload.

*— End of merged roadmap. Sequence: S0 + Track 0 now; A1→A4 for the OLI→PRD slice; then A5–A10 for the
full pipeline; Track B for Gemini; Track C in parallel; M1 after the flow is proven.*
