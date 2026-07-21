# claudster

**claudster is a Claude Code harness** — a plugin (plus a shared pool of skills, subagents, slash-commands, and hooks) that makes a single Claude Code session dramatically more capable and much harder to derail. It's *agent-agnostic*: the same pool is exported to other AI CLIs (Copilot, Codex, and more), and `CLAUDE.md`↔`AGENTS.md` are mirrors so every agent reads the same conventions.

---

## Quickstart (5 minutes)

```bash
# 1. Install the core plugin from the marketplace (always-on, lean context)
claude plugin install claudster@claudster

# 2. (optional) Add the long-tail skill library — cloud/data/media/etc. Off by default.
claude plugin install claudster-extras@claudster

# 3. In any repo, deploy the harness into the project
/setup-project-ai
```

Then a normal loop looks like:

```
/feature-plan      # (or /prd first) → writes .claudster/plans/<slug>.md, the durable spine
/implement         # executes the plan phase-by-phase, TDD, commit per phase
/ship              # commit → push → CI → prod (auto-detects Gitea / GitHub Actions / local)
/handoff           # ALWAYS end a session with this — writes the resume doc
```

**The one habit that matters most: end every session with `/handoff`.** It writes `.claudster/relay.md`, which is automatically re-injected the next time you start — so you resume with zero re-discovery instead of a cold, forgetful session.

---

## Why it exists (the problems it solves)

- **Context rot / session resume** — long sessions lose the thread. `/handoff` captures exact state into `relay.md`; a SessionStart hook re-injects it next time.
- **Knowledge evaporation** — hard-won findings vanish. A layered memory system + the `knowledge-transfer` subagent persist them into the right long-lived docs.
- **Plan drift over multi-session work** — a plan file is the durable, machine-readable spine that survives restarts and drives `/implement`.
- **Destructive mistakes** — a safety guard blocks secret/catastrophic writes and asks before dangerous shell/CI actions.
- **Same-vendor review blind spots & quota limits** — cross-vendor review and non-Anthropic model lanes (see **Providers & keys**).

---

## Key mental models

- **`.claudster/` is your repo's harness brain.** It holds `relay.md` (resume), `memory.jsonl` (auto-memory), `usage-log.jsonl`, `kb/` (knowledge base), `plans/`, and `workstreams.json`. It's repo-scoped and mostly git-ignored.
- **Relay is the anti-context-rot spine between sessions.** You write it with `/handoff`; it auto-injects on start. You rarely open it by hand.
- **Plans-as-spine.** `.claudster/plans/<slug>.md` with a `## Tracker` is the source of truth `/implement` reads and updates. The plan is the intelligence; the executor just follows it.
- **Two-plugin context tiering.** `claudster` (core) is always on; `claudster-extras` (the big skill library) stays *off* until you need it, because every skill description is a standing context tax.
- **Model-portable by design.** Everything is markdown interpreted by a CLI. A skill's `model: opus|sonnet|haiku` is a logical tier, not a hardcoded vendor.

---

## Reference

### Slash commands

| Command | What it does |
|---|---|
| `/handoff` | End-of-session resume doc; runs `knowledge-transfer` first, writes `relay.md`, names one exact next step |
| `/feature-plan` | A phased, TDD-structured plan — the durable spine for multi-session work |
| `/prd` | Requirements discovery → a PRD (headless-safe; won't interrogate on terse input) |
| `/implement` | Headless plan executor — branch-only, TDD, commit-per-phase, updates the Tracker |
| `/tdd` | A strict red-green-refactor cycle for one unit of behavior |
| `/ship` | Commit → push → monitor deploy (auto-detects Gitea, GitHub Actions, or local-only) |
| `/kb` | Rebuild the KB index (`.claudster/kb/DOC-MAP.md`) — create, reindex, prune, or check |
| `/usage-review [days]` | Analyze your usage log, surface prioritized harness tweaks, apply config changes |
| `/digress [reason]` · `/resume` | The **workstream stack** — park the current task on a detour, pop it back later |
| `/cross-review` | A second-vendor review of your current diff (see **Providers & keys**) |
| `/mermaid-db [sql\|file\|object] [out]` | Turn a SQL proc/view/query/schema into a **Mermaid** diagram (git-diffable `.md`) — deterministic structure from `sqlglot`, business narration on top |
| `/excalidraw-db [sql\|file\|object]` | Same, as an **Excalidraw** diagram for a design review / ARB / slide (drag-the-boxes, higher-level) |
| `/setup-project-ai` | Install/refresh the harness into a project |

**DB diagramming (`/mermaid-db`, `/excalidraw-db`).** Both take a SQL artifact — a file path, a
database object name (looked up via a DB MCP tool or read-only `sqlcmd`/`psql`), pasted SQL, or the
current file — and explain it as a diagram. The `db-diagram` skill's `sql_to_graph.py` extracts the
structure *deterministically* as a strict pipeline (tables `[(T)]` / CTEs `{{CTE: name}}` → one `WHERE`
box → result → projection, joins with keys labelled on the edges) so diagrams diff cleanly and
regenerate on schema change; the
model adds the business-terms explanation and per-table descriptions. Both are **read-only** (never
DDL/DML) and **never guess schema** (inferred-from-SQL-text-only elements are marked). Examples:

```bash
/mermaid-db dbo.usp_GetActiveSubscriptions            # look up the proc, diagram it → docs/diagrams/usp_GetActiveSubscriptions.md
/mermaid-db ./queries/revenue_rollup.sql docs/diagrams/revenue.md   # a .sql file → a chosen path
/mermaid-db                                            # diagram the SQL in the current file / paste
/excalidraw-db Customers Orders Invoices               # multiple tables → ONE relationship diagram for a review
```
Requires `pip install sqlglot` for the deterministic parse (pure-Python, no DB driver); without it the
skill hand-parses from the SQL text and marks everything inferred.

### Skills (the pool)

Skills are focused capability modules Claude loads on demand. They're grouped by category in `.github/skills/_registry.md`:

- **Coding** — api-design, backend-development, code-review, refactoring, security-review, sql, cross-review, anchor-review…
- **Frontend** — frontend-design, css-architecture, react-dev, mockup, warm-editorial-ui…
- **Planning / Workflow** — brainstorming, golden-plan, writing-plans, preflight, context-curator, state-tracking…
- **Testing** — tdd-workflow, playwright, test-strategy
- **Docs** — technical-writing, code-documentation, document-skills (docx/pdf/pptx/xlsx)
- **Data / DevOps / Media / Cloud** — schema & migration, git-commit, worktrees, mermaid, draw-io, AWS/Cloudflare…

The core set ships in `claudster`; the long tail lives in `claudster-extras` (enable when needed).

### Subagents

Lean, own-context helpers that do a job and report back (they don't clutter your main thread):

- **anchor** — evidence-first verification for high-risk changes (read-only)
- **code-reviewer** — reviews a diff, returns a verdict + issue list
- **preflight** — validates a plan against the *actual* codebase before you build
- **tester**, **debug**, **codebase-audit**, **security-analyst**, **data-engineer**, **sql-expert**
- **knowledge-transfer** — captures durable lessons into your long-lived docs after a session

### The four-layer memory model

1. **Session relay** — `relay.md`, written by `/handoff`, injected at SessionStart/PreCompact.
2. **Dream Memory** — `memory.jsonl`, **automatic**: mines your session transcripts for failure-modes and red→green wins, decays over time, surfaces the top few at start. Secrets are redacted; it fails open.
3. **Knowledge base** — `.claudster/kb/*.md` indexed by `DOC-MAP.md`; a coverage check keeps links honest.
4. **Cross-repo memory** — durable per-repo facts under `~/.claude/projects/<slug>/memory/`.

### Hooks & safety

- **guard.py** (PreToolUse) — blocks secret/catastrophic writes, asks before destructive shell/CI/lockfile changes. Tunable via `.claudster/config.toml [guard]`.
- **auto_lint.py** (PostToolUse) — lints on Edit/Write.
- **inject_relay.py** / **session_end.py** — the SessionStart/Stop hooks behind relay + memory.

### Digression tracker

When a task detours into a different one, you don't lose the original:

```
/digress blocked on the auth bug     # parks the current plan+phase on a LIFO stack
...do the detour...
/resume                              # pops it back with its exact resume point
```

Parked work is surfaced at the top of every session start (`⛏ Parked workstream: …`). It's metadata-only — it never touches your git working tree.

### Export & publishing

The same pool is exported to other AI CLIs (`export_runtime_resources.py` + `.github/runtime-targets.json`: targets for `claude`, `copilot`, `codex`, and more). Distribution is handled by `sync.ps1`:

- `junai-push` (default) — **mirror-sync only**, bumps the plugin version, pushes the marketplace mirror. **No publish.**
- `junai-push -Publish` / `junai-release` — also publishes the MCP server (PyPI) + VS Code extension. Use deliberately.

Quality gates before shipping: `validate_pool.py` and `python -m pytest scripts/tests`.
