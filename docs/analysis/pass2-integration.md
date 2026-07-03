# Pass 2 — Claudster×Docket Integration + ClaudsterOS

**Author:** Claude (Fable 5), Pass 2 of 2 — integration mechanism, packaging, idea→ship pipeline, ClaudsterOS.
**Date:** 2026-07-03
**Inputs:** direct inspection of `E:\Projects\claudster-source` and `E:\Projects\docket` (every claim cited), plus external research (Chase's video, osiris, worldmonitor.app).
**Citation convention:** `claudster:<path>:<line>` = `E:\Projects\claudster-source\<path>`; `docket:<path>:<line>` = `E:\Projects\docket\<path>`.

## Executive summary

Claudster and docket are already coupled — docket ships a working, tested, two-directional file contract against `.claudster/` (plan `status:` frontmatter → lane; lane handoff → plan scaffold + `docket_id` frontmatter), and both projects ship stdio FastMCP servers. What is missing is exactly one component: an **agent-runner** that turns a board action into a headless Claude Code session and renders the result back. Claudster has **no web UI anywhere** (verified: zero webviews across all VS Code extensions; its "dashboards" are static markdown), while docket has a complete FastAPI + React SPA with dark mode, charts, and a project switcher. Therefore ClaudsterOS should not be a new product: it is a **command-center view inside docket's existing web app**, fed by docket's existing event log extended with a small closed set of `agent.run.*` lifecycle events. The runner lives inside `docket serve` (docket's write-serialization is in-process, so an external writer would race), spawns `claude -p` with the claudster plugin loaded, and communicates through the file contract that already works. Claudster does **not** need to become a standalone harness — Claude Code is the harness; claudster stays plugin-shaped and gains only a tiny headless-mode convention in its skills. The packages stay **separate**, coupled by versioned contracts, because their release cadences, dependency sets, and audiences are different. The smallest valuable slice — drag a card into a "PRD" lane → headless `/prd` runs → the PRD renders in the card drawer — is fully specified in Part 2 and touches ~9 files in docket and 1 file in claudster.

## Headline verdicts

- **Integration mechanism:** Hybrid — **"runner + file contract + one board log; MCP in-session."** Trigger = a new agent-runner inside `docket serve` spawning headless `claude -p` sessions (not docket-as-MCP-client, not a merged runtime). Artifacts = the existing `.claudster/{prd,plans}` file contract, unchanged. Lifecycle = new `agent.run.*` event types appended to docket's `events.jsonl` (its reducer already skips unknown types, so this is a forward-compatible extension). MCP's role is **in-session**: the spawned agent uses docket's 25 MCP tools to write back to the board and (later, for multi-stage) claudster's `junai-mcp` to drive pipeline state. The two MCP servers stay **two servers**.
- **Packaging:** **Separate.** Claudster keeps its `junai-push` triple-publish (plugin → marketplace mirror, `junai-mcp` → PyPI, VS Code ext); docket publishes independently (PyPI `docket` + its Claude Code plugin). Coupling is by versioned contract (frontmatter schema + `agent.run.*` event schema + headless invocation convention), documented in docket's build spec ("spec is law"). No umbrella package, no monorepo, no `claudster[docket]` extra in v1.
- **Registry vs parallel engine:** Docket never grows a stage engine. In v1 the lane→command mapping is pure config (one lane, one skill) and auto-advance reuses docket's **existing** `status_lane_map` sync — that is a lane↔status lookup, not a transition engine. When multi-stage autopilot arrives (deferred, gated on v1 proving out), stage semantics are driven by **claudster's `transitions.py`/`agents.registry.json` via `junai-mcp`** — never re-implemented in docket. Honest constraint: claudster's pipeline state is single-active-pipeline-per-repo (`pipeline_init` guard), so the full OLID track has an inherent WIP limit of 1 agent pipeline per repo.
- **Bridge vs single event log:** **Single UI-facing log = docket's `events.jsonl`.** There is no true second event log today — claudster's "transition registry" is current-state plus capped in-file history (`_notes._routing_history`, 50-cap), not an append-only log. Don't build a bidirectional event bridge; the runner translates run outcomes into board events, and pipeline-state remains the stage authority for the (single) active pipeline.
- **Smallest end-to-end slice:** **OLI→PRD.** Opt-in agent-track lane "PRD": card drag → `agent.run.queued` → runner spawns `claude -p "/prd …"` in the linked repo → `.claudster/prd/<slug>.md` written → `agent.run.completed` with artifact path + highlights → card drawer renders the PRD (new artifact endpoint + markdown renderer). Human reviews; **no auto-advance** in the slice.
- **Plugin vs harness (integration angle):** **Claudster stays a plugin.** Board→agent triggering requires a runner and a headless entry point into *Claude Code*, not a claudster runtime. The runner seam (CLI spawn) plus the MCP seam (in-session tools) make claudster fully drivable by docket while remaining plugin-shaped. Nothing in Workstreams D or F requires claudster to own a process loop.
- **Anchor corrections:** (1) `lavish-axi` **does not exist** in claudster's working tree or git history — treat it as an unbuilt external dependency, not an available transport; the slice is designed to not need it. (2) "docket reads/watches `.claudster/`" is imprecise: docket also **writes** `.claudster/backlog/` and surgically manages `docket_id` frontmatter in plans (non-destructively). (3) Docket's MCP server has **25** tools, not ~15. (4) There is no file-watcher anywhere: docket's "watch" is a Claude Code `PostToolUse` hook plus manual/API sync.

---

# Phase 0 — What I found (cited grounding)

## 0.1 Claudster's state machine: pipeline-runner

- **Location:** `claudster:.github/tools/pipeline-runner/` — `pipeline_runner.py` (1,807 lines), `transitions.py`, `schema.py`, `guards.py`, `agents.registry.json`, `junai.py`, tests.
- **Stages:** 22, declared in `agents.registry.json:3-26` (`intent, intake, prd, architect, security, plan, ux_research, ui_design, preflight, implement, anchor, tester, review, debug, knowledge_transfer, devops, janitor, sql_design, accessibility, data_engineer, closed, BLOCKED`), each mapped to an agent file.
- **Transitions:** the registry JSON is the single source of truth (`claudster:.github/tools/pipeline-runner/transitions.py:22-45` loads it at import; the inline list at `transitions.py:47-199` is an explicitly dead legacy fallback, `transitions.py:200-201`). Shape: frozen dataclass `Transition(id, from_stage, to_stage, event, guards[], gate, hotfix_only, priority)` (`transitions.py:10-19`). IDs T-01…T-49 with wildcard/meta transitions (T-24/25 mode passthrough, T-26 catch-all→BLOCKED at priority −100, T-27 BLOCKED recovery).
- **Selection:** `compute_next_transition` (`pipeline_runner.py:393-482`): global escalation guard first, BLOCKED recovery second, then priority-sorted candidates matched on (stage, event) with every guard evaluated (`guards.py`). Gates (human approvals) are checked but **non-blocking** — the result carries `gate_satisfied`; in `autopilot` mode all gates except `intent_approved` auto-satisfy (`pipeline_runner.py:329-342`).
- **State persistence:** one JSON file per workspace, default `.github/pipeline-state.json` (`pipeline_runner.py:17`), Pydantic-validated (`schema.py:88-106` `PipelineState`, `extra="allow"`), deep-merge-preserving writes (`pipeline_runner.py:63-82`). Retry/phase counters live inside stage records (`schema.py:21-35`).
- **Single-active-pipeline constraint:** `pipeline_init` refuses to overwrite a non-closed pipeline (`claudster:.github/tools/mcp-server/server.py:687-710`). One `project`/`feature` at a time per state file. This matters for the OLID track (§1.5).
- **Events: none.** No callbacks, webhooks, sockets, HTTP, log-file emission, or pub/sub anywhere in the tool (verified by grep and read). The closest things are in-state capped histories: `_notes._routing_history` / `_stage_history` (50-cap, `server.py:259-280`) and `_notes._routing_decision` (`pipeline_runner.py:571-590`). Consumers must re-read the state file. All "dashboards" are static markdown (`write_dashboard` → `.github/agent-docs/pipeline-dashboard.md`, `pipeline_runner.py:1135-1167`).
- **Invocation:** CLI (`junai pipeline next|advance|skip|fast-track|…` via `junai.py`, `junai.sh`/`junai.bat` shims); in-process import by the MCP server (`server.py:44-58`); and prose-driven by the orchestrator agent (`claudster:.github/agents/orchestrator.agent.md`). Every command prints one JSON object to stdout; mutating commands write the state file.
- **Tests:** ~86 test functions across 5 modules; strong coverage of T-01…T-27 selection, guards, CLI UX, enhancements; thinner on T-28…T-49 by ID.

## 0.2 Claudster's MCP server (`junai-mcp`)

- **Location/identity:** `claudster:.github/tools/mcp-server/server.py` (913 lines), FastMCP server named `junai-mcp` (`server.py:188`), **stdio** transport (`mcp.run()` bare, `server.py:908`). Published to PyPI as `junai-mcp` **0.2.26** from the mirror checkout `claudster:vscode-extensions/junai/pyproject.toml:6-8` (source byte-identical to the canonical file; `sync.ps1:1212-1225` copies on hash drift). The MCP-registry `server.json` is stale at 0.1.1.
- **11 tools** (the dir README undersells at 9): `notify_orchestrator` (record stage completion → deterministic next transition via in-process pipeline-runner import, `server.py:205-284`), `validate_deferred_paths`, `get_pipeline_status`, `skip_stage`, `set_pipeline_mode`, `satisfy_gate`, `update_notes` (single-writer path for `_notes`), `replay_stage`, `pipeline_init`, `pipeline_reset`, and — significantly — **`run_command`** (`server.py:799-904`): shell exec in workspace root, 600s hard cap, Windows `CREATE_NEW_PROCESS_GROUP` + `CTRL_BREAK_EVENT` handling.
- **What this server is:** a *pipeline-state* server. It does not run agents, does not know about `.claudster/` artifacts, and has no event surface. `run_command` proves out the Windows subprocess pattern the new runner needs (process groups, timeout kill, output caps).

## 0.3 Claudster's skills, hooks, artifacts — and the headless reality

- **Hooks** (`claudster:claude-harness/hooks/hooks.json`): PreToolUse `guard.py` (deny/ask/allow safety tiers with a `.claudster/config.toml` downgrade-only escape hatch, `guard.py:161-172`); SessionStart + PreCompact `inject_relay.py` (injects `.claudster/relay.md`, DOC-MAP pointer, Dream-Memory facts); Stop `session_end.py` (handoff nudge, usage digest → `.claudster/usage-log.jsonl`, Dream-Memory capture → `.claudster/memory.jsonl`); PostToolUse `auto_lint.py`. All pure-Python and fail-open.
- **Commands are interactive-only.** `/prd` runs a prose discovery interview (`claudster:claude-harness/commands/prd.md:13-21`); `/feature-plan` reads code and may dispatch a preflight subagent (`feature-plan.md:17-32`); `/ship` is an operator-driven commit→push→CI→prod monitor with Gitea/GitHub/local auto-detect (`ship.md:14-20`). **No headless path exists in the harness**: no `claude -p` usage in `claude-harness/`; the only real headless invocations in the repo are skill-creator eval scripts (`claudster:.github/skills/workflow/skill-creator/scripts/improve_description.py:21,45` — which also documents the `CLAUDECODE` env-removal trick for nested spawns) and an *archived, unimplemented* autopilot watcher design (`claudster:.github/agent-docs/.archive/pipeline/PIPELINE-BACKLOG.md:417,452`).
- **Artifact contract as implemented:** `/prd` → `.claudster/prd/<feature-slug>.md`; `/feature-plan` → `.claudster/plans/<feature-slug>.md`. Frontmatter emitted by both (`prd.md:24-33`, `feature-plan.md:52-60`):

  ```yaml
  ---
  type: prd | plan
  status: draft
  feature: <feature-slug>
  creation-agent: claudster
  Original Author: Claude Code
  Creation Date: <ISO-8601Z>
  Creating Model: <model-id>
  ---
  ```

  Canonical `status:` enum is `draft|current|done|superseded` (`claudster:claude-harness/claude-md/root.md.tmpl:57-70`). Real artifacts in the wild confirm the shape — docket's own repo contains six claudster-authored PRD/plan pairs, e.g. `docket:.claudster/plans/projects-repo-sync.md:1-9` (`type: plan`, `status: draft`, `feature: projects-repo-sync`). Note the lifecycle mismatch: plans commonly stay `status: draft` even when the body says complete — docket's `status_lane_map` deliberately tolerates this (`draft → In Progress`).
  Other `.claudster/` residents: `relay.md`, `kb/` + `DOC-MAP.md`, `memory.jsonl`, `usage-log.jsonl`, `reviews/`, `PROJECT-FACTS.md`, `config.toml` (all cited in the harness inspection; `prd/`, `plans/`, `reviews/` are created on demand).
- **`lavish-axi`: absent.** No match for `lavish-axi`/`lavish_axi`/`axi` in the working tree **or in full git history** (`git rev-list --all` grep); the only "lavish" hit is a Google-font CSV row. The interview-transport dependency the task brief assumes available is **not built**. Consequence: the smallest slice must run without an interview transport (headless-mode convention instead); an interview loop rendered in the docket UI is a future phase with an explicit dependency flag.

## 0.4 Claudster build & publish

- **Export:** `claudster:export_runtime_resources.py` (repo root) builds per-target bundles from the canonical `.github/` pool into `dist/runtime-resources/<target>/` per `claudster:.github/runtime-targets.json` — 6 targets: `copilot`, `ptarmigan`, `liffey`, `codex`, **`claude`** (the `claudster` plugin, v1.3.14, workspace `plugin`, ~38 core skills flattened), **`claude-extras`** (v1.3.2). Post-export privacy scan fails the build on leaked private names.
- **Publish:** `claudster:sync.ps1` `junai-push` (`sync.ps1:1048-1389`) mirrors the pool into `vscode-extensions/junai/` (a checkout of the separate `saajunaid/junai` marketplace-mirror repo), auto-bumps plugin versions on content change, commits/pushes the mirror, then — gated on **key presence, not content diff** — cascades into `junai-release` (`sync.ps1:1680-1810`): `junai-publish-mcp` (build + twine → PyPI) and `vsce publish` for the `junai-labs.junai` VS Code extension. `-NoPublish` skips the PyPI/VSCE legs. The authoring repo and the mirror are separate remotes (`claudster:README.md:32-34`).
- **Current versions:** plugin `claudster` 1.3.14, `claudster-extras` 1.3.2, PyPI `junai-mcp` 0.2.26, VS Code `junai` 1.2.35, `ptarmigan` 0.1.40, `liffey` 0.1.18 (internal VSIX).

## 0.5 Claudster web UI audit: **none exists**

Exhaustive grep across `claudster:vscode-extensions/**` for webview APIs (`createWebviewPanel`, `registerWebviewViewProvider`, `contributes.views`, …) returned **zero matches**. The three TS extensions (junai-vscode, ptarmigan, liffey — near-identical `src/`) surface everything through OutputChannels, an integrated terminal, and quick-picks. `pipeline-runner` has no HTTP surface (§0.1). The MCP servers are stdio-only. **There is no "minimal webUI" to extend — the ClaudsterOS decision starts from zero on the claudster side.**

## 0.6 Docket's event-sourcing core

- **Envelope:** exactly five keys `{id, ts, actor, type, data}` (`docket:src/docket/events.py:63-71`); ISO-8601 UTC `Z` timestamps; ULID event ids (`evt_<ulid>`, monotonic → self-sorting log). Real example: `docket:.docket/events.jsonl:1`.
- **Closed type set:** 19 types (`events.py:14-44`): `task.created/updated/moved/archived/linked`, `subtask.*`, `checklist.*`, `label.*`, `milestone.*`, `todo.captured`, `commit.linked`, `comment.added`, `attachment.added/removed`. **The reducer logs and skips unknown types for forward compatibility** (`docket:src/docket/reducer.py:277-280`) — the extension point the integration uses.
- **Reducer:** pure, no I/O, no wall clock (`reducer.py:259-284`); invariant `reduce(read_events()) == board.json` (spec §10). Task shape at `reducer.py:28-59` already includes `project` and `plan_path`, set by `task.linked` (`reducer.py:92-98`).
- **Store/engine:** append is a plain `open("a")` line write (`docket:src/docket/store.py:69-70`); `board.json` writes are atomic (`store.py:38-43`). **Write serialization is a per-repo in-process `threading.RLock`** (`docket:src/docket/engine.py:89-117`) wrapping all 20 write ops; the comment explicitly warns multi-process writers need an on-disk lock. `_commit` = append → full replay → write board → best-effort notifications (`engine.py:141-153`). **Consequence: the agent-runner must live inside the `docket serve` process (or call its API), never write the log from a second process.**
- **No watcher.** Nothing tails `events.jsonl`; the log is replayed on write or lazily on read (`engine.py:128-138`). Grep for watchdog/watchfiles/inotify: nothing.

## 0.7 Docket's MCP server, API, hooks

- **MCP:** **25 tools** (spec §6 said ~15; the build outgrew it), stdio FastMCP (`docket:src/docket/mcp_server.py:16,242-247`), every tool a thin wrapper over `engine` with `repo_path="."` default. Full list at `mcp_server.py:213-239`: reads (`get_board`, `get_task`, `get_tasks` w/ filters, `search_tasks`), task writes (`create_task`, `update_task`, `move_task`, `assign_and_advance`, `archive_task`, `add_subtask`, `complete_subtask`, `add_comment`, `add_attachment`), checklist/labels/milestones (7), hooks back-channel (`capture_todos`, `link_commit`), projects (`link_task`, `sync_repo`), charts (`get_chart_data`). Wired by `docket:plugin/.mcp.json` → `docket mcp` console script.
- **API:** FastAPI + uvicorn, `docket serve --port 8732` (`docket:src/docket/cli.py:68-73`), ~40 endpoints under `/api` mirroring the engine ops, JWT/RBAC auth **off by default** (open mode actor "claude", `api.py:289-291`), attachments hardened (magic-byte sniff, Pillow re-encode). In prod the same service serves the built React SPA under `/docket/` (`api.py:1099-1148`) behind IIS — matching claudster's `windows-deployment` shape.
- **Hooks** (`docket:plugin/hooks/hooks.json`): PostToolUse `Write|Edit|MultiEdit` → `docket hook capture-todos` **and** `docket hook sync-plan`; PostToolUse `Bash` → `docket hook link-commit`. `sync-plan` self-filters to `.claudster/plans/*.md` edits then runs a full repo sync (`docket:src/docket/hooks.py:75-92`). Hooks never raise (exit 0 always).
- **Agent-runner: none.** The only subprocesses in docket are read-only git calls (`config.py:61`, `hooks.py:36`, `version.py:39`). Docket is a passive board today.

## 0.8 Docket's Projects feature: how `.claudster/` is read AND written today

This is the load-bearing existing integration — more complete than the task brief assumed:

- **Repo → board (read-back):** `docket:src/docket/sync.py:31-52` iterates tasks with a `plan_path`, parses the plan's frontmatter `status:` with a no-YAML scalar parser (`docket:src/docket/projection.py:42-55`), maps it through `config.status_lane_map` (`draft→In Progress, in-progress→In Progress, review→In Review, done→Done`, `docket:src/docket/config.py:35-40`), and emits **idempotent** `task.moved` events — only into repo-authoritative lanes (`In Progress/In Review/Done` = keys of `lane_status_map`, `sync.py:39-47`). Inbox/Backlog stay docket-owned. Zero ping-pong by construction.
- **Board → repo (projection):** `engine.move_task` → `_project_lane_change` (`docket:src/docket/engine.py:387-437`), opt-in via `config.projects_enabled` (default **false**, and false in docket's live config `docket:.docket/config.json:19`): entering Backlog writes `.claudster/backlog/<id>-<slug>.md`; the Backlog→In Progress handoff scaffolds-or-links `.claudster/plans/<slug>.md` and stores `plan_path` on the task via `task.linked`. Writes are **surgical, non-destructive** frontmatter merges — only docket-managed keys (`docket_id`, and `status` only when scaffolding a new stub) are touched, byte-preserving everything else including EOLs (`projection.py:106-135`).
- **Ownership correction to the anchors:** docket doesn't merely "read/watch" `.claudster/` — it owns `.claudster/backlog/` outright and co-manages one frontmatter key (`docket_id`) in plans. Claudster owns plan/PRD bodies and `status:`. This split is documented and tested (`docket:.claudster/prd/projects-repo-sync.md` G3: "Zero sync ping-pong — no lane both sides write, by construction").
- **`_project_lane_change` is the natural trigger point** for the agent-runner: it is already the place where a lane move causes side effects outside the board, already best-effort/never-raises, and already opt-in via config.

## 0.9 Docket's web UI

- React 18.3 + Vite 5 + TypeScript; **@tanstack/react-query v5 is the only state layer**; @dnd-kit for drag; recharts for charts; hand-written plain CSS (1,650-line `styles.css`) with CSS custom properties and **first-class dark mode** (`docket:web/src/hooks/useTheme.ts`).
- Board: lanes from `board.lanes`, cards sorted by float `position`; drag-end computes `{lane, beforeId}` and fires `POST /api/tasks/{id}/move` with optimistic update + invalidation (`docket:web/src/hooks/useMoveTask.ts`, `web/src/api/client.ts:224-233`). Card detail = `CardDrawer.tsx` (446 lines) with full editing, bug fields, linked-plan section, attachments.
- **No push channel:** board refreshes only via mutation-invalidation + refetch-on-focus; the sole poller is notifications at 30s (`docket:web/src/hooks/useNotifications.ts:21-22`, comment "(no WebSocket)"). **No markdown rendering anywhere** (no react-markdown/dangerouslySetInnerHTML) — artifact render-back needs a new dependency.
- Views: `"board" | "insights" | "users"` union (`docket:web/src/components/Sidebar.tsx:12`), switched by `useState` — no router. Adding a `"command"` view is a ~10-line wiring change plus the view component. `Insights.tsx` (CFD/throughput/burndown) and `lib/boardStats.ts` KPI helpers are directly reusable for command-center panels.
- Prod serving: the FastAPI service serves the SPA (`api.py:1099-1148`) — one Windows service behind IIS.

## 0.10 Docket packaging

`docket` 0.1.0, hatchling, `requires-python >=3.11`, deps `python-ulid, fastapi, uvicorn[standard], mcp, pyjwt, bcrypt, python-multipart, Pillow` (`docket:pyproject.toml:1-28`). Console script `docket` with subcommands `mcp | serve | sync | hook {capture-todos,link-commit,sync-plan} | user` (`cli.py:14-59`). Claude Code plugin at `docket:plugin/` (plugin.json v0.1.0 + `.mcp.json` + hooks.json). **Not on PyPI**; installed editable via uv. Gitea CI + Windows/IIS deploy docs in-repo.

## 0.11 Anchor confirmations & corrections

| Anchor (from brief) | Verdict after inspection |
|---|---|
| Directory ownership settled: claudster writes `.claudster/`, docket owns `.docket/` and reads/watches `.claudster/` | **Mostly confirmed, one correction:** docket also *writes* `.claudster/backlog/` and manages the `docket_id` frontmatter key in plans — surgically and non-destructively (`projection.py:106-135`). No watcher exists; "watch" = PostToolUse hook + manual/API sync. |
| Claudster stages map ~1:1 to OLID lanes | **Confirmed with nuance.** intent/intake≈OLI, prd≈PRD, plan(+architect/preflight)≈IPD, implement≈IID, tester+review(+anchor)≈IVD, closed/ship≈ISD. Claudster's machine has 22 stages incl. optional tracks — the OLID lanes are a coarse projection, which is fine because lanes are a view, not the engine (§1.5). |
| Both ship MCP servers | **Confirmed.** `junai-mcp` 0.2.26 (11 tools, pipeline-state domain) and `docket` (25 tools, board domain). Zero overlap in tool domains. |
| Claudster skills interactive today; no `claude -p` path | **Confirmed** (§0.3). |
| `lavish-axi` is the natural interview transport, assume available | **Corrected: it does not exist in the codebase or its history.** Stated as a hard dependency flag; the v1 slice avoids needing it. |
| Windows/NSSM production shape | **Confirmed both sides:** docket serves SPA+API as one service behind IIS; claudster ships a `windows-deployment` skill; `junai-mcp.run_command` already handles Windows process groups. |

## 0.12 Headless Claude Code facts (docs-verified; blockers flagged)

Verified against official Claude Code docs (headless.md, cli-reference.md, sessions.md, agent-sdk docs):

- **Slash commands work in `-p` mode** — "include `/skill-name` in the prompt string and Claude Code expands it before running" (headless.md). This makes `claude -p "/prd …"` a legitimate invocation.
- **Plugins/hooks/MCP load by default in `-p` mode** — the `--bare` flag exists specifically to *skip* "auto-discovery of hooks, skills, plugins, MCP servers, auto memory, and CLAUDE.md", implying the default is discovery-on. (Empirical smoke test still required — validation gate in Part 2 Phase 2.)
- **Programmatic flags:** `--output-format json|stream-json`, `--permission-mode` (incl. `acceptEdits`, `bypassPermissions`), `--allowedTools`, `--max-turns`, `--model`, `--resume <session-id>`. `stream-json` emits one JSON object per line (`system/init` carries loaded plugins/skills).
- **AskUserQuestion in raw `-p` is undocumented** (may hang or no-op). Two consequences: (1) v1 prompts must explicitly forbid interviewing (headless-mode convention in the skill); (2) the *documented* interception mechanism is the Agent SDK's `can_use_tool` callback — which is the natural future replacement for the absent `lavish-axi` interview transport (a Python SDK callback pumping questions into the docket UI).
- **Exit codes are not documented** → success detection must be (a) parse the `-p --output-format json` result envelope and (b) **deterministic artifact existence check** — which the Part 2 design uses as the primary signal.
- **Windows-service auth:** docs indicate `-p` under a service should use `ANTHROPIC_API_KEY` (+ optionally `CLAUDE_CONFIG_DIR`); logged-in keychain credentials in service context are unverified. **BLOCKER assumption to smoke-test before Phase 2 sign-off.**

---

# Part 1 — Decision Document

## 1.1 Research: build / adopt / skip

| Source | What it is (verified) | Ruling | Rationale |
|---|---|---|---|
| **Chase's video** (youtube.com/watch?v=HRw-vP0j8OM, "The Agentic OS Setup That Will 10x Claude Code", Chase AI, ~late June 2026) | Four-layer "Agentic OS": (1) Obsidian-vault markdown memory + root CLAUDE.md; (2) recurring tasks codified as skills; (3) cron/scheduled automations; (4) a web dashboard where **every skill is a clickable button that triggers `claude -p` headlessly**, plus usage/vault-activity/schedule widgets. Templates gated behind a paid community; no public repo. | **Adopt the shape, not the artifact.** | The proposal is architecturally identical to what claudster+docket already half-own: claudster *is* layers 1–2 (KB/Dream-Memory + skills), docket *is* the board the dashboard wants to be. The one component Chase adds that we lack is the headless trigger loop — exactly Workstream F's missing agent-runner. Nothing to buy or clone; the video validates the direction. |
| **simplifaisoul/osiris** (github.com/simplifaisoul/osiris — verified: exists, MIT, Next.js 16 + MapLibre OSINT dashboard, ~6.4k stars, active as of 2026-07-02) | Real-time global-intelligence dashboard ("Palantir alternative"): 16 toggleable layers, map-centric, Vercel-deployed. | **Skip (aesthetic reference only).** | Different stack (Next.js vs docket's Vite SPA), different domain, and adopting it means owning a large codebase for its looks. Its panel-density ideas are already captured better by the worldmonitor token set below. |
| **worldmonitor.app** (open source: koala73/worldmonitor; actual CSS tokens extracted from `src/styles/main.css` + `panels.css`) | Terminal/SIGINT "operations room" aesthetic: near-black layered grays (`#0a0a0a/#111/#141414/#1e1e1e`), 1px hairline borders (`#2a2a2a`), 4–8px radii, 12px monospace body, 9–11px UPPERCASE tracked-out muted panel headers, 4px grid gaps, saturation reserved for severity (`#ff4444/#ff8800/#ffaa00/#44aa44/#3388ff/#44ff88`), tabular numerals, hidden scrollbars, 0.1s hovers. | **Adopt as the command-center design recipe.** | Concrete, extractable, and compatible with docket's CSS-custom-property theming (scope the tokens to a `.command` view class; keep the rest of the app in docket's existing indigo/zinc look). Zero code adoption — tokens only. |
| **lavish-axi** (interview transport, per brief) | **Does not exist** in `claudster-source` working tree or full git history (§0.3). | **Cannot adopt; design around it.** | v1 slice uses a headless-mode skill convention (no questions; unresolved items go in the PRD's "Open questions" section). The future interview loop should be built on the **Claude Agent SDK `can_use_tool` callback** (documented) pumping AskUserQuestion payloads into a docket UI question panel — flagged as the Pass-1 reconciliation point. |

## 1.2 Workstream D verdict — ClaudsterOS is a docket view, not a product

**D.1 — Existing claudster webUI:** none (§0.5). The audit result is: nothing to extend on the claudster side; a "ClaudsterOS webUI" built there would start from an empty directory *and* would still need docket's data to be useful.

**D.3 (decided first, because it drives everything): one product.** The command center and the kanban are the same surface. Reasons, in order of weight:

1. **The board *is* the command deck.** The V.A.U.L.T. screenshot's "command deck of canned intents queued to a runner" is functionally a lane of cards mapped to commands — which is precisely the F-workstream agent-track. Building a second queue UI means two queues over one runner.
2. **Docket already owns every hard part:** served SPA + API in one Windows service (§0.9, §0.10), auth/RBAC when wanted, project switcher (multi-repo — the command center's scope selector for free), dark-mode CSS-variable theming, charts, and a KPI helper (`boardStats.ts`). A separate ClaudsterOS frontend duplicates all of it.
3. **One event layer** (mandated by the brief): D's feed and F's lifecycle events are both served by the extended `events.jsonl` + `/api` — impossible to split-brain if there is only one consumer surface.
4. **Solo-user test:** two web apps to keep open, deploy, and update for one person is bloat by definition.

**D.2 — Requirements met as follows:**
- (a) *Trigger headless sessions on demand/schedule:* on-demand = agent-track lane drags + a "Run" button per card + command-deck buttons (Phase 5); scheduled = deferred (§1.9 open question — Claude Code's native scheduling/cron via `/schedule` may cover it without docket owning a scheduler).
- (b) *Structured panels, not a chat transcript:* panels = Runs feed (from `agent.run.*` events), Queue (queued runs), Active agents (running runs w/ elapsed), KPI tiles (board stats + run success rate), Artifact activity (recent `.claudster/` artifacts from run records), Directives (pinned cards). Token/tool-level streaming is explicitly **not** rendered in v1 (stream-json tool-event format is undocumented, §0.12); the run's stream is captured to a log file for debugging.
- (c) *Reads as a command center:* worldmonitor token recipe scoped to the new view (§1.1).

**D.4 — Architecture:** no new backend service. The runner is a component **inside `docket serve`** (mandatory anyway — docket's write lock is in-process, §0.6). Feed transport: **v1 = React Query polling** (`refetchInterval` ~2s only while a run is active/queued — cheap and consistent with the existing stack); **v2 = SSE** endpoint (`GET /api/events/stream`) once the command center proves daily use. Extending `pipeline-runner` or either MCP server into a web backend is rejected: pipeline-runner is a CLI with no server (§0.1), and MCP stdio servers are per-client child processes, not shareable daemons. Windows/NSSM: unchanged — still exactly one service.

**Explicitly not building (bloat flags, solo-user test applied):** voice I/O, webcam PiP, central animated visualization (V.A.U.L.T. theater — zero workflow value for one user at a desk), geopolitical-monitor panels (worldmonitor is an aesthetic reference only), metric sparklines beyond what recharts already renders, and any "any coding agent" generalization before the Claude Code flow ships (§1.6 seam 5 keeps the config shape harness-ready without building a second harness).

## 1.3 Integration-mechanism verdict

**Chosen: hybrid — "runner + file contract + one board log; MCP in-session."**

| Mechanism | Role in the hybrid | Why not more / less |
|---|---|---|
| **(a) File contract** (`.claudster/{prd,plans,backlog}` + frontmatter) | **Kept as-is for all artifacts.** Already implemented, tested, non-destructive, and human-inspectable (§0.8). The runner's success signal is artifact existence + frontmatter parse — deterministic, no protocol needed. | As the *only* mechanism it cannot trigger anything (docket has no watcher, and adding one to watch for triggers is inversion of control by polling — fragile on Windows filesystems). |
| **(b) Event bridge** (`events.jsonl` ⇄ transition registry) | **Rejected as a bridge; adopted as a one-way translation.** New `agent.run.*` types are appended to docket's log by the runner (in-process, lock-safe). Claudster's pipeline-state is not an event log (§0.11) — there is nothing on the other side to bridge *from*; its state changes surface as run outcomes, which the runner already owns. | A true bidirectional bridge would create the split-brain the brief warns about: two writers reconciling two histories. One log, one writer per fact. |
| **(c) MCP** | **In-session, both servers, unchanged transports.** The headless agent spawned by the runner gets docket's MCP tools (it can `add_comment`, `move_task`, `link_task` — render-back richer than exit-code parsing) and claudster's `junai-mcp` (pipeline state, when the multi-stage track lands). **Not** used for docket→claudster triggering: that would make docket an MCP *client* managing a stdio child + session lifecycle — strictly more machinery than spawning `claude -p`, and `junai-mcp` has no "run an agent" tool anyway (its `run_command` runs shell commands *inside* an existing workspace, §0.2). | MCP's two advertised advantages are real but land differently: reuse-of-both-servers happens in-session; triggerable-without-harness happens via the CLI spawn (§1.7). |
| **(d) Merged runtime** | **Rejected.** Kills independent versioning (§1.4), forces kanban-only users to install the harness, and couples two release cadences that are currently 1.3.x-weekly vs 0.1.0-unpublished. | — |

**One MCP server or two? Two.** The tool domains are disjoint (board ops vs pipeline-state ops), the packaging homes are different (PyPI `docket` vs PyPI `junai-mcp`), and merging would force a shared release cadence for zero UX gain (Claude Code loads both trivially). Revisit only if tool-count context pressure appears (docket's descriptions are already ≤2 sentences by spec §6 for this reason).

**Trigger contract in one sentence:** a lane move (or Run button / MCP `run_agent` call) enqueues a run; the runner spawns `claude -p "<command + card context + headless-mode instructions>"` with `cwd` = the linked project repo; the session writes artifacts via claudster skills and optionally writes back via docket MCP; the runner detects the artifact deterministically, appends `agent.run.completed|failed`, and the UI re-renders. Full schemas in Part 2.

## 1.4 Packaging verdict — separate, contract-coupled

**Ship separately.** Concretely:

- **claudster** keeps its current triple-artifact flow unchanged: `junai-push` → plugin `claudster` (marketplace mirror), `junai-mcp` (PyPI), VS Code ext (§0.4). The integration adds exactly one pool file change (headless-mode section in `commands/prd.md`) → next plugin patch (1.3.15) via the existing bump machinery.
- **docket** becomes independently publishable: PyPI `docket` (pyproject is ready; it has never been published) + its Claude Code plugin (`docket:plugin/`). The runner, events, and command-center view all live here, versioned as docket 0.2.x.
- **The contract is the coupling**, versioned in `docket:docket-build-spec.md` (docket's "spec is law" file) as a new section "§11 Agent-track contract v1": artifact paths + frontmatter keys consumed (`type`, `status`, `feature`, `docket_id`), the `status_lane_map` semantics, the `agent.run.*` event schemas, and the headless invocation convention. Claudster's side of the contract (frontmatter emitted by `/prd`//`/feature-plan`) is already stable and documented in the command files themselves.
- **No umbrella package.** `pip install claudster[docket]` is rejected: claudster-the-plugin isn't pip-installed (it's a Claude Code marketplace plugin), so the extra would sit on `junai-mcp` — the wrong home. A `docket[agent]` extra is also unnecessary: the runner needs **zero new Python deps** (stdlib subprocess) — the only new dependency in the whole slice is `react-markdown` in the web app.
- **Consistency check (mechanism ⇄ packaging ⇄ event-log):** separate packages ⇄ coupling by file/CLI/MCP contracts ⇄ single board log owned by docket, single pipeline state owned by claudster. Nothing shares a runtime; nothing shares a release; the UI is one product but it ships wholly inside docket.

**Versioning/release model:**

| Artifact | Owner | Cadence | Integration impact |
|---|---|---|---|
| `claudster` plugin (1.3.14 → 1.3.15) | claudster repo, `junai-push -NoPublish` for pool-only changes | content-hash auto-bump | +headless-mode prd section (Part 2 Phase 3) |
| `junai-mcp` 0.2.26 | claudster repo, `junai-publish-mcp` | manual, on MCP change | **no change in v1** |
| `docket` 0.1.0 → 0.2.0 | docket repo (PyPI first publish) | semver-minor per phase group | runner + events + API (+plugin hooks unchanged) |
| Contract "agent-track v1" | `docket-build-spec.md` §11 | frozen per major | breaking change ⇒ v2 section + config `schema_version` bump |

## 1.5 Registry vs parallel engine — and the event-log ruling

**Ruling 1: docket never gets a stage engine.** The lane→command map in config (Part 2 §P2) is a lookup table, not a transition system: no guards, no gates, no priorities, no wildcards. All of that stays in `agents.registry.json` + `guards.py` where it is already implemented and tested (§0.1).

**Ruling 2: auto-advance v1 reuses docket's existing sync, not a new engine.** When a headless `/feature-plan` writes `status: draft`, docket's *existing* `status_lane_map` + `sync_repo` already move the card (`docket:src/docket/sync.py:31-52`). Extending that map to OLID lane names is configuration, not code. This is the "smallest thing that delivers value" answer to auto-advance: the mechanism shipped in docket's Projects feature *is* the stage-advance mechanism for artifact-producing stages.

**Ruling 3: when multi-stage autopilot lands (deferred), claudster's registry drives it.** The runner (or the in-session agent) calls `junai-mcp`: `pipeline_init` on track entry, `notify_orchestrator(stage_completed, result_status, artefact_path)` on each run completion, and the returned `TransitionResult.next_stage` — computed by `compute_next_transition` against T-01…T-49 — maps back to a lane via config. Docket renders; claudster decides. **Hard constraint to surface now:** pipeline-state is one-active-pipeline-per-repo (`server.py:687-710`), so the OLID track has an inherent WIP limit of 1 per repo. For a solo user this is a feature (focus), but it must be enforced in the UI (the track refuses a second in-flight card) rather than discovered as a `pipeline_init` error.

**Ruling 4 (bridge vs single log): single log.** Docket's `events.jsonl` is the only append-only history in the system and the only one a UI reads. Claudster's `_notes._routing_history` (50-cap, overwritten in place) is diagnostic state, not a log. The runner translates outcomes → board events one-way. If the full OLID track later needs stage-level history in the UI, the runner appends `agent.stage.advanced` events *at translation time* (same writer, same log) — never by tailing claudster state. Split-brain is avoided by the same rule docket already proved with lanes: **every fact has exactly one writer** (run lifecycle: runner; stage authority: pipeline-state; board state: engine; artifact bodies: claudster skills).

## 1.6 Docket-readiness: the five seams

| # | Seam | Status | Evidence | Minimal exposure needed |
|---|---|---|---|---|
| 1 | **Artifact-storage contract** (naming + frontmatter linking artifact↔card↔stage) | **HAVE (≈90%)** | `.claudster/{prd,plans}/<feature-slug>.md`; frontmatter `type/status/feature` emitted by claudster (`prd.md:24-33`), `docket_id` merged by docket (`projection.py:159-175`); `status_lane_map` read-back shipped (`sync.py`) | Nothing new for the slice. Later: extend `status_lane_map` for OLID lane names; optionally have `/prd` accept a `docket_id` to stamp at creation (nice-to-have; the runner can merge it post-hoc through docket's own `_merge_frontmatter`). |
| 2 | **Headless invocation contract** (input = card + prior artifacts; output = deterministic artifact + machine-readable highlights) | **MISSING** — the core gap | No `claude -p` path in the harness (§0.3); no runner in docket (§0.7) | The agent-runner (Part 2 P2): prompt template assembling card fields + prior-artifact paths; success = artifact-exists + frontmatter parse; highlights = trailing fenced `json` block in the session result (best-effort) with deterministic fallback. |
| 3 | **Interview transport** | **MISSING; dependency absent** | `lavish-axi` does not exist (§0.3); AskUserQuestion in `-p` undocumented (§0.12) | v1: none — headless-mode convention (skill must not ask; unresolved → "Open questions" section). v2: Agent SDK `can_use_tool` callback → docket question panel. |
| 4 | **Lifecycle event emission** (subscribable stage events; shared with D's feed) | **PARTIAL** | docket's log is append-only + forward-compatible (`reducer.py:277-280`) but has no agent events and no push; claudster emits nothing (§0.1) | 4 new event types `agent.run.{queued,started,completed,failed}` + reducer handlers (Part 2 P1); UI polls v1, SSE v2. |
| 5 | **Lane↔stage mapping + config** | **PARTIAL** | `status_lane_map`/`lane_status_map` exist for 3 lanes (`config.py:35-45`); custom lanes supported (`lanes` is config); no lane→command map | `agent_track` config block: per-lane `{command, auto_advance, requires_confirmation}` (Part 2 P2). Harness field included but fixed to `claude-code` (no second harness until the first flow is proven). |

**Scope rulings (as required by the brief):** the OLID pipeline is an **opt-in track** — `agent_track.enabled` defaults false and only the configured lanes trigger anything; every other card and lane behaves exactly as today. Single-agent (Claude Code) end-to-end before any generalization. ISD→deploy is **hard-gated**: a confirmation-required run is never spawned by a drag alone (design in Part 2 P6 — the drag queues an `awaiting_confirmation` run; a typed confirmation in the UI releases it; the runner refuses unconfirmed ISD runs at spawn time as defense-in-depth; `/ship`'s own preflight gates remain a third layer).

**Smallest valuable end-to-end slice (named): OLI→PRD.** One lane move → `/prd` headless → PRD rendered in the drawer for human review. No auto-advance, no interview, no deploy. Part 2 Phases 1–4 specify it fully; it exercises seams 2, 4, and 5 (the missing ones) while riding seams 1 and 3's v1 conventions.

## 1.7 Plugin vs harness — independent take from the integration angle

**Claudster should stay a plugin.** The board→agent pipeline requires three things: something that *queues and spawns* (the runner — lives in docket), something that *executes with tools* (the harness — Claude Code itself), and something that *knows the workflow* (skills + pipeline state — claudster). Nothing in D or F requires claudster to own a process loop, a scheduler, or a transport: `claude -p` reaches its skills (docs-verified, §0.12), its MCP server already exposes pipeline state to any client, and its artifacts are plain files. Making claudster a standalone harness would mean rebuilding permissioning, tool execution, model routing, and session management that Claude Code already provides — to gain nothing the runner seam doesn't already deliver. The MCP seam softens the question exactly as the brief suspected, but the CLI-spawn seam softens it *more*: docket can drive claudster today without claudster changing shape at all beyond a headless-politeness convention in two skill files. (Reconciliation note for Pass 1: if Pass 1 concludes claudster needs harness-like internals for its *own* reasons — e.g. local-model routing — that decision is orthogonal to this integration; the runner contract stays `claude -p`-shaped either way, and a future `agent_track.harness` value could point at a different CLI.)

## 1.8 Phased roadmap (dependencies explicit)

| Phase | Repo | Delivers | Depends on |
|---|---|---|---|
| **P1** Run events + store | docket | `agent.run.*` event types, reducer, run records, spec §11 | — |
| **P2** Agent-runner + lane trigger | docket | runner in `docket serve`, `agent_track` config, spawn/detect/translate, manual `docket run` CLI | P1; BLOCKER smoke tests (headless auth under service, plugin loading in `-p`) |
| **P3** Headless-mode skill convention | claudster | `/prd` headless section; plugin 1.3.15 | none (parallel with P1/P2) |
| **P4** Render-back UI | docket web | Run panel in drawer, artifact viewer endpoint + markdown render, agent-lane badge, active-run polling | P1, P2 |
| — | — | **← smallest slice complete (OLI→PRD)** — evidence gate: screen recording of drag→PRD | P1–P4 |
| **P5** Command-center view v0 | docket web | `"command"` view: runs feed, queue, active agents, KPI tiles; worldmonitor tokens; docket MCP `run_agent`/`get_runs` tools | P4 |
| **P6** Second lane + auto-advance + ISD gate | both | `/feature-plan` headless (claudster); extended `status_lane_map`; `requires_confirmation` flow + confirm endpoint (deploy hard-gate) | P5 usage evidence |
| **P7 (deferred)** Full OLID autopilot + interview + SSE | both | pipeline-runner-driven multi-stage via `junai-mcp`; Agent SDK `can_use_tool` interview panel; SSE feed | P6 proven in daily use; Pass-1 reconciliation on interview transport |

## 1.9 Open questions for the user

1. **One UI or two** — Part 1 rules *one* (command center inside docket). Confirm you're happy retiring "ClaudsterOS" as a separate app name, or keep the name as the view's title.
2. **Bridge vs collapse event logs** — ruled *single log* (docket's), with pipeline-state as stage authority. Any reason you want claudster transition history mirrored into the board log from day one (adds `agent.stage.*` events in P2 instead of P7)?
3. **Auto-advance boundaries** — proposed: artifact-status-driven advance only (existing sync mechanism), human drag between agent lanes otherwise, nothing auto-advances *into* an agent lane in v1. Where do you want the line eventually — e.g. should IID→IVD (implement→test) ever auto-chain without a human glance?
4. **Together vs separately** — ruled *separate*. Confirm docket should get its first PyPI publish (name availability on PyPI for `docket` is unverified — may need `docket-board` or similar; flagged in Part 2).
5. **Scheduling** — command deck v1 is on-demand only. Do you want docket to own schedules (cron in the service) or lean on Claude Code's native scheduled agents for recurring runs?
6. **Interview transport** — accept "no questions in headless v1, Agent SDK callback in v2" as the lavish-axi replacement? (Pass 1 may have a different plan for lavish — reconcile there.)

## 1.10 Risk / bloat flags (each with the solo-user "worth it?" test)

| Risk | Severity | Mitigation | Worth-it test |
|---|---|---|---|
| **Two-event-logs split-brain** (board log vs pipeline-state) | High if ignored | Ruled out structurally: single UI log, one writer per fact, one-way translation (§1.5 R4). Do not build a bidirectional bridge even if it looks "more complete". | A solo user never reads two histories; they read one board. Any second history is bloat. |
| **Auto-deploy foot-gun** (drag → prod) | Critical | Three independent layers: UI typed confirmation, runner spawn-refusal without `confirmed_at`, `/ship`'s own preflight+CI gates (P6). Deploy is *never* reachable from a drag alone. | One person = no second reviewer; the machine must be the second pair of eyes. Worth every line. |
| **Headless auth under NSSM unverified** | High (blocks P2) | Smoke test first (P2 gate): `claude -p` as the service account with `ANTHROPIC_API_KEY`/`CLAUDE_CONFIG_DIR`. Fallback: run `docket serve` as a user-session process instead of NSSM during v1. | — (prerequisite, not a feature) |
| **Runaway/hung headless sessions** | Medium | `--max-turns`, run timeout + process-group kill (pattern proven in `junai-mcp.run_command`, §0.2), `max_concurrent_runs: 1` default, per-run cost surfaced in UI from the result envelope. | One stuck session on your own box is annoying; ten concurrent ones are a bill. Cap of 1 is the solo-correct default. |
| **Command-center theater** (viz, voice, webcam) | Medium (time sink) | Explicitly out of scope (§1.2). Panels must answer "what ran, what's queued, what needs me" — nothing else in v0. | If a widget doesn't change what you do next, it's decoration. |
| **Premature harness generalization** ("any coding agent") | Medium | `agent_track.harness` field exists but only `"claude-code"` is implemented; adding a second value is rejected until one flow runs for weeks. | You use one agent. Ship for it. |
| **Skill drift breaking the contract** (a future `/prd` edit changes paths/frontmatter) | Medium | Contract frozen in spec §11 + a docket test fixture containing a golden claudster frontmatter block; claudster side already treats the frontmatter block as canonical in the command file. | Cheap insurance: one fixture test. |
| **PyPI name `docket` availability** | Low | Check before P1 release; fall back to `docket-board` (console script stays `docket`). | — |

## 1.11 Docket-readiness verdict (summary)

Docket is **one component short of ready**: seams 1 and 5 are substantially built, seam 4 is a forward-compatible extension its reducer was explicitly designed to absorb, and seams 2+3 are genuinely missing but small (a runner module + a skill convention). The board→agent inversion lands almost entirely in docket (runner, events, UI), with claudster contributing one prompt-file edit in v1 — which is exactly how it should fall given the ownership split: docket owns *when* agents run; claudster owns *what* they do; Claude Code owns *how*. Registry-vs-engine: claudster's registry, when multi-stage arrives; never a docket engine. Event logs: one (docket's). Smallest slice: OLI→PRD (Part 2, next). Plugin-vs-harness: plugin.

---

# Part 2 — Build-Ready PRD: board→agent pipeline + command center

**How to use this document:** each phase is independently shippable and carries a self-contained implementation prompt — a mid-tier agent should be able to execute a phase from its prompt alone, without re-deriving any decision. Phases 1–4 are the smallest end-to-end slice (OLI→PRD) and are specified at maximum depth. Phases 5–7 are the next slices. All schemas below are normative ("spec is law" — copy §2.0 into `docket:docket-build-spec.md` as §11 during Phase 1).

**Conventions:** `docket:` paths are under `E:\Projects\docket`; `claudster:` paths under `E:\Projects\claudster-source`. Python tests run with each repo's `.venv`. Docket layering rule (must hold): `store/ids/actor/events` → `config/reducer/projection` → `engine` → transports (`mcp_server`/`api`) — the new `runner` sits beside the transports and calls only `engine`.

## 2.0 Global contracts (normative schemas — spec §11 "Agent-track contract v1")

### 2.0.1 Config: `agent_track` block (in `.docket/config.json`)

Added to `DEFAULT_CONFIG` in `docket:src/docket/config.py` (all defaults exactly as shown; the block ships disabled):

```json
"agent_track": {
  "enabled": false,
  "harness": "claude-code",
  "claude_cmd": "claude",
  "max_concurrent_runs": 1,
  "run_timeout_seconds": 1800,
  "max_turns": 50,
  "permission_mode": "acceptEdits",
  "model": null,
  "lanes": {
    "PRD": {
      "command": "/prd",
      "artifact_dir": ".claudster/prd",
      "auto_advance_to": null,
      "requires_confirmation": false
    }
  }
}
```

Semantics: `lanes` keys are **lane names** (must exist in `config.lanes`; custom names allowed — this is the lane↔stage↔command map of seam 5). `command` is the claudster slash command injected into the headless prompt. `artifact_dir` is where the runner looks for the deterministic output artifact. `auto_advance_to` (lane name or `null`): on `agent.run.completed`, move the card there (Phase 6; ignored in the slice). `requires_confirmation`: if true, a lane entry queues a run in `awaiting_confirmation` state and the runner will not spawn it until confirmed (Phase 6; the deploy hard-gate). `model`: optional `--model` override. `harness` must equal `"claude-code"` — any other value is a config error in v1 (premature-generalization guard).

### 2.0.2 Events: four new types (extend the closed set in `docket:src/docket/events.py`)

Envelope unchanged (`{id, ts, actor, type, data}`). `actor` is `"runner"` for all four. Data payloads:

```jsonc
// agent.run.queued — appended when a run is created (lane trigger, Run button, MCP, or CLI)
{ "run_id": "run_01J…",            // ids.new_run_id(), ULID-monotonic, prefix "run_"
  "task_id": "DKT-7",
  "lane": "PRD",                    // agent-track lane that triggered it
  "command": "/prd",
  "project": "E:\\Projects\\myapp", // absolute repo path the session will cwd into
  "requires_confirmation": false }

// agent.run.started — appended by the worker immediately before spawn
{ "run_id": "run_01J…", "task_id": "DKT-7" }

// agent.run.completed — artifact detected after a clean exit
{ "run_id": "run_01J…", "task_id": "DKT-7",
  "artifact_path": ".claudster/prd/my-feature.md",   // repo-relative, forward slashes
  "highlights": { "summary": "…≤280 chars…", "open_questions": 2 },  // nullable
  "duration_seconds": 312.4,
  "cost_usd": 1.87,                 // nullable — from the -p json envelope when present
  "num_turns": 23,                  // nullable
  "session_id": "abc-123" }         // nullable — enables claude --resume for follow-ups

// agent.run.failed — spawn error, timeout, non-zero/failed result, or missing artifact
{ "run_id": "run_01J…", "task_id": "DKT-7",
  "error": "timeout after 1800s" | "artifact not found at .claudster/prd/my-feature.md" | "…",
  "exit_code": 1,                   // nullable
  "duration_seconds": 1800.0 }
```

### 2.0.3 Reducer materialization (board shape additions)

`reduce()` gains a top-level `"runs": {}` map. Handlers (mirroring the `attachments` `setdefault` precedent for old tasks):

- `agent.run.queued` → `board["runs"][run_id] = {run_id, task_id, lane, command, project, status: "queued"|"awaiting_confirmation" (per requires_confirmation), queued_at: ts, started_at: None, finished_at: None, artifact_path: None, highlights: None, error: None, cost_usd: None, duration_seconds: None, session_id: None}`; append `run_id` to `task.setdefault("agent_runs", [])`; set `task["last_run"] = {"run_id": run_id, "status": <status>}`.
- `agent.run.started` → run `status="running"`, `started_at=ts`; update `task["last_run"]["status"]`.
- `agent.run.completed` → run `status="succeeded"`, `finished_at=ts`, copy `artifact_path/highlights/cost_usd/duration_seconds/num_turns/session_id`; update `task["last_run"]`.
- `agent.run.failed` → run `status="failed"`, `finished_at=ts`, copy `error/exit_code/duration_seconds`; update `task["last_run"]`.
- (Phase 6) `agent.run.confirmed` → run `status="queued"`, `confirmed_at=ts`.

All handlers no-op on unknown `run_id`/`task_id` (same defensive style as existing handlers). Determinism rule unchanged: no wall clock — all times from event `ts`.

### 2.0.4 Run working directory (heavy data stays out of the log)

`<board-repo>/.docket/runs/<run_id>/` (git-ignored) containing `prompt.txt` (exact prompt sent), `result.json` (the full `-p --output-format json` envelope, verbatim), `stderr.txt`. Event payloads carry only references/derived fields — same discipline as attachments (blobs out of the log, §0.7).

### 2.0.5 Headless invocation contract (seam 2)

Spawn (v1, exact):

```
<claude_cmd> -p "<PROMPT>" --output-format json --permission-mode <permission_mode> --max-turns <max_turns> [--model <model>]
```

- `cwd` = `run.project` (the linked project repo: `task.project` if set, else the board repo itself).
- Environment: inherit the service env; **delete `CLAUDECODE`** (nested-spawn conflict — pattern proven in `claudster:.github/skills/workflow/skill-creator/scripts/improve_description.py:30`); require `ANTHROPIC_API_KEY` or a working `CLAUDE_CONFIG_DIR` (BLOCKER B1).
- Windows: `creationflags=CREATE_NEW_PROCESS_GROUP`; on timeout send `CTRL_BREAK_EVENT`, wait 5s grace, then kill — copy the exact pattern from `claudster:.github/tools/mcp-server/server.py:833-861`.
- **Success =** process ended within timeout AND envelope's `is_error` is not true AND the expected artifact exists AND its frontmatter parses with `type:` + `feature:` (via docket's own `projection.parse_frontmatter`). Artifact-missing after a "clean" exit is a **failure** (exit codes are undocumented — the artifact is the contract, §0.12).
- Expected artifact path = `<artifact_dir>/<slug>.md` where `slug = engine._slugify(task["title"])` (`docket:src/docket/engine.py:85-86` — the same slugger the projection handoff already uses, so plan/PRD names line up).

Prompt template (v1, exact — `{…}` substituted by the runner):

````
{command} {title}

Docket card {task_id} — context:
Title: {title}
Description:
{description}

HEADLESS RUN RULES (mandatory):
- You are running non-interactively. No user is present. Do not ask questions, do not use
  AskUserQuestion, do not pause for confirmation or approval at any point.
- Derive everything you need from the context above and from the codebase; anything you cannot
  resolve goes under an "## Open questions" section of the artifact instead of being asked.
- Write the artifact to {artifact_dir}/{slug}.md with the standard frontmatter, using
  feature: {slug} so the filename and frontmatter agree.
- End your final message with exactly one fenced json block:
  ```json
  {"artifact": "{artifact_dir}/{slug}.md", "summary": "<one sentence, <=280 chars>", "open_questions": <count>}
  ```
````

Highlights parsing: take the **last** fenced `json` block in the envelope's `result` string; validate it is an object with an `artifact` key; on any parse failure fall back to `highlights = null` (the deterministic artifact check is the success signal, not this block).

### 2.0.6 HTTP API additions (all under `/api`, same auth/RBAC posture as existing write endpoints)

```
POST /api/tasks/{task_id}/run          body: {"lane": "PRD"?}        → 200 run record (as in §2.0.3)
       lane defaults to the task's current lane; 400 if that lane is not in agent_track.lanes
       or agent_track.enabled is false; 409 if max_concurrent_runs would be exceeded.
GET  /api/runs?task_id=&status=        → 200 [run records], newest first
GET  /api/runs/{run_id}                → 200 run record; 404 unknown
GET  /api/artifacts?path=<rel>&project=<name>?   → 200 {"path": "...", "frontmatter": {...}, "body": "..."}
       Guards (all enforced): path must be relative; resolved path must stay under the repo root
       AND under .claudster/; extension must be .md; size cap 1 MiB; 404 if absent.
POST /api/runs/{run_id}/confirm        (Phase 6) body: {"confirm_text": "DKT-7"} → 200; releases
       an awaiting_confirmation run only when confirm_text equals the run's task_id exactly.
```

`GET /api/board` response is decorated at the API layer (not stored in board.json) with `"agent_track": {"enabled": bool, "lanes": {<lane>: {"command": str, "requires_confirmation": bool}}}` so the web app can badge agent lanes without a second request.

### 2.0.7 Artifact/frontmatter contract (seam 1 — restated, already live)

Claudster emits (`claudster:claude-harness/commands/prd.md:24-33`, `feature-plan.md:52-60`): `type: prd|plan`, `status: draft|current|done|superseded`, `feature: <slug>`, `creation-agent: claudster`, plus authorship keys. Docket manages exactly one key in plans, `docket_id`, via surgical merge (`docket:src/docket/projection.py:106-135`), and maps plan `status:` → lane via `status_lane_map`. The runner links artifacts to cards by (a) the run record's `artifact_path` and (b) post-run `docket_id` frontmatter merge using `projection._merge_frontmatter` (never a body rewrite). **Golden fixture:** docket's test suite gains `tests/fixtures/claudster_prd_frontmatter.md` holding a verbatim claudster frontmatter block; a test asserts `parse_frontmatter` extracts `type/status/feature` from it (skill-drift tripwire, §1.10).

---

## Phase 1 — `agent.run.*` events + reducer + run records (docket)

**Goal:** the board can represent agent runs end-to-end (queued→running→succeeded/failed) purely as events, with the replay invariant intact — before any process is ever spawned.

**Files:**
- `docket:src/docket/events.py` — add the 4 types (+ `agent.run.confirmed` reserved, commented) to `EVENT_TYPES`.
- `docket:src/docket/ids.py` — add `new_run_id()` returning `run_<ulid>` (mirror `new_event_id`).
- `docket:src/docket/reducer.py` — add `"runs": {}` to the board skeleton in `reduce()`; add the 4 handlers per §2.0.3; register in `_HANDLERS`.
- `docket:src/docket/engine.py` — add `_serialized` ops: `queue_agent_run(repo_path, task_id, lane, *, command, project, requires_confirmation=False, now=None) -> dict` (validates task exists + lane exists, allocates `run_id`, commits `agent.run.queued`, returns the run record), `start_agent_run(repo_path, run_id, *, now=None)`, `complete_agent_run(repo_path, run_id, *, artifact_path, highlights=None, duration_seconds=None, cost_usd=None, num_turns=None, session_id=None, now=None)`, `fail_agent_run(repo_path, run_id, *, error, exit_code=None, duration_seconds=None, now=None)`. Each is a thin `_commit` wrapper like every existing op.
- `docket:docket-build-spec.md` — new §11 with the §2.0 schemas verbatim ("spec is law": events added to §3's closed set, board shape to §4, reducer rules to §5).
- `docket:tests/test_events.py`, `docket:tests/test_reducer.py`, `docket:tests/test_engine.py` — coverage below.
- `docket:.gitignore` — add `.docket/runs/`.

**Implementation prompt (self-contained):**
> In `E:\Projects\docket`, extend the event-sourced core with agent-run lifecycle events. Read `src/docket/events.py`, `reducer.py`, `engine.py` (`_commit` at :141, `_serialized` at :109), `ids.py`, and spec §§2–5 of `docket-build-spec.md` first. Add event types `agent.run.queued|started|completed|failed` to the closed set; data payloads and reducer materialization exactly per the "§11 Agent-track contract v1" section you will also add to `docket-build-spec.md` (copy it from `E:\Projects\claudster-source\docs\analysis\pass2-integration.md` §2.0.2–§2.0.3). Add `ids.new_run_id()` with prefix `run_`. Board gains a top-level `"runs"` map; tasks gain `agent_runs` (list, `setdefault` for old tasks) and `last_run`. Add four engine ops (`queue_agent_run`, `start_agent_run`, `complete_agent_run`, `fail_agent_run`) as `_serialized` `_commit` wrappers with `actor="runner"`; `queue_agent_run` raises `TaskNotFound`/`InvalidOperation` on bad ids/lanes. No subprocess code in this phase. TDD: write failing tests first in `tests/test_reducer.py` (each handler; unknown run_id no-op; determinism — same events twice ⇒ equal boards), `tests/test_events.py` (types in set), `tests/test_engine.py` (full queue→start→complete replay; `reduce(read_events()) == board.json` invariant after the sequence; `fail` path). Keep the reducer pure — all timestamps from event `ts`. Gitignore `.docket/runs/`.

**Acceptance criteria:** four types in `EVENT_TYPES`; reducer handlers registered; engine ops exist and are serialized; spec §11 present; old logs still reduce identically (no behavior change for existing types).

**Validation gate:** `E:\Projects\docket\.venv\Scripts\python -m pytest tests/ -q` → all green (baseline suite + new tests). Reconstruct check: delete `.docket/board.json` in a scratch repo fixture, call `engine.get_board`, assert equality with pre-delete board.

**Evidence:** pytest output; a scratch `events.jsonl` showing the four-event sequence and the resulting `board.json` `runs` entry.

---

## Phase 2 — the agent-runner + lane trigger (docket)

**Goal:** a lane move (or CLI call) actually spawns a headless claudster session and translates the outcome into Phase-1 events. This is seam 2 — the missing component.

**Files:**
- `docket:src/docket/runner.py` (new, ~250 lines) — queue + worker + spawn + detection:
  - `class Runner`: `deque` of pending run_ids per repo, `threading.Thread` worker (daemon), `threading.Event` wake signal; constructed with nothing, started via `runner.start()`.
  - `enqueue(repo_path, task_id, lane, *, source) -> dict`: loads config; validates `agent_track.enabled`, lane in `agent_track.lanes`, active-run count < `max_concurrent_runs` (else `InvalidOperation`); resolves `project` (task's `project` field or `str(Path(repo_path).resolve())`); calls `engine.queue_agent_run`; wakes the worker; returns the record.
  - Worker loop: pop → re-read run from board (skip if `awaiting_confirmation`) → `engine.start_agent_run` → `_execute(run)` → `complete_agent_run` / `fail_agent_run`. Every branch wrapped so an exception becomes `fail_agent_run`, never a dead worker.
  - `_execute`: build prompt per §2.0.5 template (card title/description fetched via `engine.get_task`; `slug = engine._slugify(title)`; lane config supplies `command`/`artifact_dir`); write `prompt.txt`; `subprocess.Popen([claude_cmd, "-p", prompt, "--output-format", "json", "--permission-mode", pm, "--max-turns", str(mt)] + (["--model", m] if m else []), cwd=project, env=env_without_CLAUDECODE, stdout=PIPE, stderr=PIPE, creationflags=CREATE_NEW_PROCESS_GROUP on win32)`; `communicate(timeout=run_timeout_seconds)` with the CTRL_BREAK→grace→kill pattern from `claudster:.github/tools/mcp-server/server.py:833-861`; persist `result.json`/`stderr.txt`; artifact check + frontmatter parse per §2.0.5; parse highlights (last fenced json block, fail-soft); post-hoc `projection._merge_frontmatter(artifact_abs, {"docket_id": task_id}, "")`.
  - Module-level singleton `runner = Runner()` and `get_runner()`.
- `docket:src/docket/engine.py` — in `move_task`, after `_project_lane_change(...)` (`engine.py:398`), add best-effort `_maybe_enqueue_agent_run(repo_path, cfg, task_id, to_lane)`: lazy-import runner, no-op unless `agent_track.enabled` and `to_lane` in `agent_track.lanes` and the task's `last_run` isn't already queued/running for that lane; never raises (mirror `_project_lane_change`'s discipline, `engine.py:434-437`).
- `docket:src/docket/config.py` — `agent_track` block in `DEFAULT_CONFIG` per §2.0.1 (+ `_ensure_agent_track` in-memory migration mirroring `_ensure_triage_lane`, `config.py:87-101`).
- `docket:src/docket/api.py` — endpoints per §2.0.6 (`POST /tasks/{id}/run`, `GET /runs`, `GET /runs/{id}`, `GET /artifacts`) + board decoration + start `runner` in the FastAPI lifespan when any served repo enables the track.
- `docket:src/docket/cli.py` — `docket run <task-id> [--lane L] [--repo .]`: synchronous one-shot (enqueue + run worker body inline, print the final record as JSON) — the no-server test path.
- `docket:tests/test_runner.py` (new) — see gate.
- `docket:tests/fixtures/fake_claude.py` (new) — a stub "claude" executable: reads argv, writes a valid artifact (frontmatter + body) into the expected path under its cwd, prints a fake `-p` json envelope including a trailing highlights block; variants via env flag: `FAKE_CLAUDE_MODE=ok|no_artifact|hang|error`.

**Implementation prompt (self-contained):**
> In `E:\Projects\docket`, build the agent-runner. Prereq: Phase 1 merged (engine ops `queue_agent_run`/`start_agent_run`/`complete_agent_run`/`fail_agent_run` exist). Read `src/docket/engine.py` (locks :89-117, `move_task` :387-400, `_project_lane_change` :403-437), `config.py`, `api.py` (app construction + lifespan), `cli.py`, and §2.0 of `E:\Projects\claudster-source\docs\analysis\pass2-integration.md` — the config block, spawn contract, prompt template, and API shapes there are normative. Implement `src/docket/runner.py` exactly as specified (single daemon worker, `max_concurrent_runs` respected, every failure path lands in `fail_agent_run`). The runner must call engine ops only (never `store.append_event` directly) so the per-repo lock holds. Wire the lane trigger into `move_task` as a best-effort call that can never break a move. Add the four API endpoints with the path-traversal guards written in §2.0.6 (test them). Add `docket run` to the CLI. For tests, do NOT call the real `claude`: `tests/fixtures/fake_claude.py` is spawned via `sys.executable` by pointing `agent_track.claude_cmd` at it (list-form command: store `claude_cmd` as string but allow the runner to split on `::` into `[python, script]` for tests — or simpler: set `claude_cmd` to a `.bat`/`.cmd` shim path in the fixture tmpdir on Windows). Test matrix in `tests/test_runner.py`: happy path (drag into PRD lane ⇒ queued⇒running⇒succeeded, artifact linked, `docket_id` merged into frontmatter, highlights parsed); `no_artifact` ⇒ failed with the exact error string; `hang` ⇒ timeout kill ⇒ failed; `error` envelope ⇒ failed; lane not configured ⇒ 400 at API/`InvalidOperation` at engine; concurrency cap ⇒ 409; artifact endpoint rejects `..`, absolute paths, non-`.md`, paths outside `.claudster/`. Board invariant must still hold after every scenario (`reduce(read_events()) == board.json`).

**Acceptance criteria:** dragging a card into the configured "PRD" lane on an `agent_track.enabled` repo produces a run that reaches `succeeded` with a real artifact when a real `claude` is on PATH; all fake-claude scenarios behave per matrix; a move into a non-agent lane spawns nothing; disabling the track restores today's behavior byte-for-byte.

**Validation gate:**
1. `python -m pytest tests/ -q` → green.
2. **BLOCKER smoke tests (must pass before this phase is called done):**
   - **B1 (auth under service context):** on the target Windows box, run `claude -p "Say OK" --output-format json` from a non-interactive context (e.g. `Start-Process` under the service account / a scheduled task) with `ANTHROPIC_API_KEY` set; assert a JSON envelope returns. If keychain-only auth fails headless, document the required env in `docs/DEPLOY.md`.
   - **B2 (plugin loading in `-p`):** in a repo with claudster installed, `claude -p "/prd smoke-test-feature" --output-format json --max-turns 40` and confirm `.claudster/prd/smoke-test-feature.md` appears — proving slash-command expansion + plugin discovery in print mode (docs say yes, §0.12; verify empirically).
3. End-to-end: `docket run DKT-<n>` against a scratch repo with the real CLI → run record `succeeded`, artifact exists.

**Evidence:** pytest output; the B1/B2 command transcripts; the scratch repo's `events.jsonl` tail (queued/started/completed) + `result.json`.

---

## Phase 3 — headless-mode convention in `/prd` (claudster)

**Goal:** `/prd` behaves correctly when no human is present: no interview, deterministic output path, highlights block emitted.

**Files:**
- `claudster:claude-harness/commands/prd.md` — add a short `## Headless mode` section after the discovery-interview section (`prd.md:13-21`): *"If the invocation includes the marker `HEADLESS RUN RULES`, skip the discovery interview entirely. Derive answers from the provided context and the codebase; put anything unresolved under `## Open questions`. Never ask the user anything. Honor the requested output path and `feature:` slug exactly. End your final message with the single fenced json highlights block requested by the invoker."*
- (Phase 6 repeats this for `feature-plan.md`; do only `prd.md` now.)
- Publish: `junai-push -NoPublish` → plugin **1.3.15** (pool-only change; per `claudster:README.md:20-31` this bumps + mirrors without republishing PyPI/VSCE).

**Implementation prompt (self-contained):**
> In `E:\Projects\claudster-source`, edit `claude-harness/commands/prd.md` only. Read the file first. After the "Discovery" section, add a `## Headless mode` section with the exact behavior: marker `HEADLESS RUN RULES` in the invocation ⇒ no interview, no AskUserQuestion, derive-don't-ask, unresolved items to `## Open questions`, honor the caller-specified output path and `feature:` slug, end with the caller-requested single fenced json highlights block. Do not change the frontmatter template or the interactive flow. Then run the quality gates: `python -m pytest scripts/tests claude-harness/hooks/tests -q` (expect the full suite green — 242 at last count) and `python validate_pool.py`. Publish with `junai-push -NoPublish` and verify the plugin version bumped to 1.3.15 in the mirror's `plugin/.claude-plugin/plugin.json`.

**Acceptance criteria:** interactive `/prd` unchanged (interview still happens without the marker); with the marker, a `-p` run produces the artifact without asking anything (B2 smoke re-run passes with zero questions in the transcript).

**Validation gate:** claudster suite green; `validate_pool.py` OK; B2 transcript shows no interview turns; plugin 1.3.15 visible in the mirror.

**Evidence:** diff of `prd.md`; pytest + validate output; mirror commit hash.

---

## Phase 4 — render-back UI (docket web): the slice becomes visible

**Goal:** the human can see everything from the board: agent-lane badge, run status on the card, and the PRD rendered in the drawer.

**Files:**
- `docket:web/package.json` — add `react-markdown` + `remark-gfm` (the app's first markdown capability, §0.9).
- `docket:web/src/api/types.ts` — `Run` type per §2.0.3 record; `Task` gains `agent_runs?: string[]`, `last_run?: {run_id: string; status: RunStatus}`; `Board` gains `runs: Record<string, Run>` and `agent_track?: {...}` per §2.0.6 decoration.
- `docket:web/src/api/client.ts` — `runTask(taskId, lane?)` → `POST /api/tasks/{id}/run`; `getRuns(params)`, `getRun(id)`; `getArtifact(path, project?)`.
- `docket:web/src/hooks/useRuns.ts` (new) — query keyed `["runs", taskId]`; `useBoard` (`web/src/hooks/useBoard.ts:5-8`) gains conditional `refetchInterval: 2000` while any board run is `queued|running` (else off — no idle polling).
- `docket:web/src/components/Lane.tsx` — "⚡ agent" pill on lanes present in `board.agent_track.lanes` (beside the existing "repo" pill, `Lane.tsx:41-44`).
- `docket:web/src/components/Card.tsx` — status dot for `task.last_run` (`queued` gray / `running` pulsing amber / `succeeded` green / `failed` red).
- `docket:web/src/components/CardDrawer.tsx` — new "Agent runs" section: run list (status chip, lane, elapsed/duration, cost when present, error on failure), a "Run agent" button when the card's lane is an agent lane, and — for a succeeded run — an "Open artifact" control.
- `docket:web/src/components/ArtifactView.tsx` (new) — fetches `GET /api/artifacts`, renders frontmatter as a compact key/value header + body via `react-markdown` w/ `remark-gfm`, inside the drawer (slide-over panel), `overflow-y` scrolling.
- `docket:web/src/styles.css` — `.run-chip` states, `.artifact-view` typography (reuse existing CSS vars; no new palette).

**Implementation prompt (self-contained):**
> In `E:\Projects\docket\web`, add run visibility and artifact rendering. Prereqs: Phases 1–2 merged (API serves `/api/runs`, `/api/artifacts`, decorated `/api/board`). Read `web/CLAUDE.md`, `src/api/types.ts`, `src/api/client.ts`, `src/hooks/useBoard.ts`, `src/components/{Lane,Card,CardDrawer}.tsx`, and `styles.css` theming vars first; follow the house rules (React Query is the only state layer; plain CSS with vars; no new state libs). Implement the file list above. The drawer's "Run agent" button calls `runTask` and invalidates `["board"]` + `["runs", taskId]`; while any run on the board is queued/running, `useBoard` polls at 2s and stops when idle (derive from the previous response inside `refetchInterval`'s function form). ArtifactView must render the real claudster PRD shape (frontmatter block + GFM tables/checklists in the body). Keep bundle discipline: `react-markdown` + `remark-gfm` only, no syntax-highlighter in v1. `npm run build` (tsc + vite) must pass; add a vitest for the run-status chip mapping and for the client's artifact-path encoding.

**Acceptance criteria:** drag card → pill'd lane shows the card's amber pulsing dot within 2s; on completion the dot turns green, the drawer lists the run with duration/cost, and "Open artifact" renders the PRD with tables/headings correctly in both themes; a failed run shows the error string; non-agent lanes/cards look exactly as today.

**Validation gate:** `npm run build` green; `npx vitest run` green; `python -m pytest tests/ -q` still green (API additions covered in Phase 2 tests).

**Evidence — the slice's exit artifact:** a screen recording (or 4-screenshot sequence) of: (1) card dragged into PRD lane, (2) pulsing running state, (3) green completed chip with cost, (4) the rendered PRD in the drawer. This recording is the OLI→PRD slice's definition of done.

---

## Phase 5 — Command-center view v0 + MCP run tools

**Goal:** the ClaudsterOS surface: one new view answering "what ran, what's queued, what's running, what needs me" — styled as an operations room.

**Files:**
- `docket:web/src/components/Sidebar.tsx` — `View` union (`Sidebar.tsx:12`) gains `"command"`; nav button.
- `docket:web/src/App.tsx` — render branch (no router needed, §0.9).
- `docket:web/src/components/CommandCenter.tsx` (new) — panel grid: **Active** (running runs w/ live elapsed), **Queue** (queued + awaiting_confirmation w/ confirm affordance placeholder), **History** (last 20 runs: status/lane/task/duration/cost, click→opens the card drawer), **KPI tiles** (reuse `lib/boardStats.ts` totals + run success-rate/total-cost derived from `board.runs`), **Artifacts** (recent `artifact_path`s, click→ArtifactView), **Needs attention** (failed runs + cards in review lanes). Reuse `Insights.tsx`'s `Panel` primitive and chart components where they fit.
- `docket:web/src/styles.css` — `.command`-scoped worldmonitor token set (from §1.1, exact values): bg `#0a0a0a`/surface `#141414`/hover `#1e1e1e`, border `#2a2a2a`, 4px radii/gaps, 12px monospace body (`'Cascadia Code', 'SF Mono', Consolas, monospace` — Windows-first), 9–11px uppercase tracked muted panel headers, semantic colors `#ff4444/#ffaa00/#44aa44/#3388ff/#44ff88`, `font-variant-numeric: tabular-nums`. Scoped under `.command` so the rest of the app keeps its identity; respect the light theme by mapping the same roles to the existing light vars (command view may stay dark-preferred but must not break the toggle).
- `docket:src/docket/mcp_server.py` — 3 new tools (thin engine/runner wrappers, descriptions ≤2 sentences per spec §6): `run_agent(task_id, lane=None, repo_path=".")` → enqueue (so an *interactive* Claude session can say "run the PRD agent for DKT-7"); `get_runs(task_id=None, status=None, repo_path=".")`; `get_run(run_id, repo_path=".")`.
- `docket:tests/test_mcp.py`, `docket:tests/test_runner.py` — tool registration + enqueue-via-MCP path.

**Acceptance criteria:** the view loads from existing queries only (board + runs — no new backend beyond MCP tools); every panel answers its question at a glance in both themes; clicking through history→drawer→artifact works; MCP `run_agent` enqueues identically to the API path.

**Validation gate:** `npm run build` + vitest green; pytest green; screenshot pair (dark command view / light board view) reviewed against the §1.1 recipe.

**Evidence:** screenshots; MCP tool-call transcript enqueueing a run from an interactive Claude session.

---

## Phase 6 — second lane (`/feature-plan`), auto-advance, and the ISD deploy hard-gate

**Goal:** prove the pattern generalizes to a second stage, wire artifact-status auto-advance through the *existing* sync machinery, and implement the deploy gate.

**Files & design:**
- `claudster:claude-harness/commands/feature-plan.md` — same `## Headless mode` section as Phase 3 (→ plugin 1.3.16).
- `docket:src/docket/config.py` — example OLID track config documented in spec §11 (lane names are user-choice; canonical example):

  ```json
  "lanes": ["OLI", "PRD", "IPD", "IID", "IVD", "ISD", "Done"],
  "agent_track": { "enabled": true, "lanes": {
      "PRD": {"command": "/prd",          "artifact_dir": ".claudster/prd",   "auto_advance_to": null, "requires_confirmation": false},
      "IPD": {"command": "/feature-plan", "artifact_dir": ".claudster/plans", "auto_advance_to": null, "requires_confirmation": false},
      "ISD": {"command": "/ship",         "artifact_dir": null,               "auto_advance_to": null, "requires_confirmation": true}
  }},
  "status_lane_map": {"draft": "IID", "in-progress": "IID", "review": "IVD", "done": "Done"},
  "lane_status_map": {"IID": "in-progress", "IVD": "review", "Done": "done"}
  ```

  Auto-advance for artifact-producing stages is **exactly the shipped sync** (`docket:src/docket/sync.py`) with remapped lane names — no new engine (§1.5 R2). `auto_advance_to` on run-completion is implemented in the runner (one `engine.move_task` call) but ships `null` everywhere by default.
- **ISD hard-gate (three layers, all mandatory):** (1) `requires_confirmation: true` ⇒ `queue_agent_run` writes status `awaiting_confirmation`; the UI queue panel shows a confirm box requiring the **task id typed exactly** (`POST /api/runs/{id}/confirm`, §2.0.6) which appends `agent.run.confirmed`; (2) the runner's worker independently refuses to spawn any run whose lane config requires confirmation unless `confirmed_at` is set (defense against API bugs); (3) `/ship` itself keeps its preflight/CI/health gates (`claudster:claude-harness/commands/ship.md:27-77`). `artifact_dir: null` ⇒ success signal for ISD runs is the `-p` envelope only plus `/ship`'s structured report in `result.json`; the run's highlights carry the deploy SHA.
- `docket:src/docket/runner.py`, `api.py`, `reducer.py` (confirmed event), `docket:web` (confirm UI in CommandCenter Queue panel + drawer).
- Tests: confirmation matrix (unconfirmed never spawns — assert after a forced worker pass; wrong confirm_text 400; confirmed spawns once), auto-advance single-fire, second-lane happy path with fake-claude.

**Acceptance criteria:** IPD drag produces a plan that then drives IID/IVD lanes through the existing sync as its `status:` changes; an ISD drag alone **cannot** start a run (verified by test *and* by manual drag); a typed confirmation releases exactly one run.

**Validation gate:** both suites green (`docket: pytest tests/ -q`; `claudster: pytest scripts/tests claude-harness/hooks/tests -q` + `validate_pool.py`); manual evidence of the confirm flow; recording of PRD→IPD→(status edit)→IVD card movement.

---

## Phase 7 (deferred — do not start without P6 usage evidence)

Scoped now only to keep earlier phases honest, per §1.8: (a) **multi-stage autopilot** — runner calls `junai-mcp` (`pipeline_init` on track entry; `notify_orchestrator` per completed run; `TransitionResult.next_stage` → lane via config), WIP-1-per-repo enforced in UI (§1.5 R3); (b) **interview transport** — replace raw `-p` with the Python Agent SDK in `runner._execute`, intercepting `AskUserQuestion` via `can_use_tool` into a question queue rendered in the command center (the lavish-axi successor — reconcile with Pass 1 first); (c) **SSE feed** (`GET /api/events/stream`) replacing the 2s poll; (d) `agent.stage.advanced` events if stage history is wanted in the UI. Each item gets its own PRD when unlocked.

---

## 2.8 Global quality gate (applies to every phase)

1. **Determinism invariant:** `reduce(read_events()) == board.json` after every new code path (docket spec §10) — asserted in tests touching writes.
2. **Full suites green, both repos:** `docket: .venv\Scripts\python -m pytest tests/ -q` · `claudster: .venv\Scripts\python -m pytest scripts/tests claude-harness/hooks/tests -q` (242 baseline) + `python validate_pool.py`.
3. **Layering:** runner calls engine ops only; reducer stays pure; API/MCP stay thin; no new writer ever touches `events.jsonl` outside `engine._commit`.
4. **Opt-in safety:** with `agent_track.enabled: false` (the default), every diff must be behaviorally invisible — a dedicated regression test drags cards across all lanes and asserts zero `agent.run.*` events.
5. **Windows-first:** every subprocess uses the process-group pattern; every path comparison is separator-tolerant (docket's `_is_plan_path` precedent, `hooks.py:75-78`); CI/dev commands avoid pytest-xdist (per `junai-mcp` warning, `server.py:810-814`).
6. **No blind trust in the model:** success is artifact-existence + frontmatter parse; highlights are best-effort; costs surfaced in UI.
7. **Contract freeze:** any change to §2.0 schemas bumps the spec §11 version and gets a migration note.

## 2.9 BLOCKER assumptions (verify before/at the marked phase)

| # | Assumption | Verified? | Verify at | Fallback |
|---|---|---|---|---|
| B1 | `claude -p` authenticates in a non-interactive Windows service context via `ANTHROPIC_API_KEY`/`CLAUDE_CONFIG_DIR` | **No** (docs silent on NSSM; §0.12) | Phase 2 gate | run `docket serve` as a user-session autostart instead of NSSM for v1 |
| B2 | Slash-command expansion + plugin auto-discovery work in `-p` (docs say yes; unproven on this box) | Docs-verified only | Phase 2 gate | pass `--plugin-dir`; worst case invoke the skill body via prompt text |
| B3 | Headless `/prd` completes within `max_turns: 50` / 30 min on a real repo | **No** | Phase 2 e2e | raise caps per-lane in config |
| B4 | `AskUserQuestion` never fires when the skill is instructed not to ask (undocumented behavior if it does) | **No** | Phase 3 B2 re-run | Agent SDK `can_use_tool` interception (Phase 7b) |
| B5 | PyPI name `docket` is available | **No** | before first publish | `docket-board` (console script stays `docket`) |
| B6 | `lavish-axi` (interview transport) — **confirmed absent**; nothing in P1–P6 depends on it | ✔ (absence verified) | — | Phase 7b design |
| B7 | Single-active-pipeline-per-repo is acceptable as the OLID WIP limit | User decision | before Phase 7a | per-feature state files (a claudster change — Pass 1 territory) |
