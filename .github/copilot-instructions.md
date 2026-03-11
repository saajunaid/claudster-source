# Copilot Instructions — agent-sandbox

> **Read this file first.** It gives you the full context of what this workspace is, how it works, and what every file does.

---

## What This Workspace Is

**agent-sandbox** is the authoring and source-of-truth repository for the **junai agent pipeline system** — a structured, multi-agent AI workflow for software development. It is not a deployed application. It is the place where all agent definitions, skills, prompts, and tooling are authored, tested, and published.

Everything in `.github/` here is the **pool source** that gets bundled into the [junai VS Code extension](https://marketplace.visualstudio.com/items?itemName=junai-labs.junai) (`junai-labs.junai`) and deployed into any project that installs it.

---

## Repository Layout

```
agent-sandbox/
├── .github/
│   ├── agents/              ← 25 agent definition files (*.agent.md)
│   ├── skills/              ← Reusable skill bundles (domain knowledge packs)
│   ├── prompts/             ← Reusable prompt files
│   ├── instructions/        ← Coding convention files (*.instructions.md)
│   ├── tools/
│   │   └── mcp-server/
│   │       └── server.py    ← FastMCP server (9 tools, runs over stdio)
│   ├── agent-docs/
│   │   ├── ARTIFACTS.md     ← Artefact registry (inter-agent working files)
│   │   └── *.md             ← Pipeline schema docs, artefact templates
│   ├── plans/               ← Implementation plans produced by the Plan agent
│   ├── handoffs/            ← Agent-to-agent handoff templates
│   ├── diagrams/            ← Architecture and workflow reference diagrams
│   ├── pipeline-state.json  ← Live pipeline state (gates, routing, artefacts)
│   └── project-config.md   ← Project-specific token definitions
├── validate_agents.py       ← Pre-publish gate: checks 25 agents + MCP smoke test
├── sync.ps1                 ← junai-pull / junai-push sync functions
└── project-config.md        ← Workspace-level config
```

> **agent-sandbox has no git remote.** All commits are local only. Changes are pushed downstream via the publish workflow described below.

---

## The Three-Repo System

```
agent-sandbox  (local only — authoring source)
    │
    ├──▶  E:\Projects\junai-vscode   (VS Code extension — github.com/saajunaid/junai-vscode)
    │         bundle-pool.js copies .github/ → pool/ before every publish
    │
    └──▶  E:\Projects\junai          (public pool mirror — github.com/saajunaid/junai)
              sync.ps1 junai-push copies .github/ folders and git pushes
```

- **agent-sandbox** is where you author all changes
- **junai-vscode** is what marketplace users install; it bundles the pool and deploys it into workspaces
- **junai** is the public-facing mirror of the pool for users who want to browse or fork agent definitions directly

---

## The 25 Agents

Each agent is defined in `.github/agents/<name>.agent.md` with a YAML frontmatter block specifying `name`, `model`, `tools`, `handoffs`, and `description`, followed by detailed behavioral instructions for the agent.

### Model Assignments

| Model | Agents |
|-------|--------|
| Claude Opus 4.6 | `anchor`, `architect` — highest-rigor work |
| Claude Sonnet 4.6 | `orchestrator`, `plan`, `prd`, `prompt-engineer`, `security-analyst`, `accessibility`, `code-reviewer`, `debug`, `mentor`, `project-manager`, `ux-designer`, `ui-ux-designer`, `knowledge-transfer` |
| GPT-5.3-Codex | `implement`, `streamlit-developer`, `frontend-developer`, `data-engineer`, `devops`, `janitor`, `sql-expert`, `tester` |
| Gemini 3.1 Pro (Preview) | `mermaid-diagram-specialist`, `svg-diagram` — visual artifact generation only |

> Gemini is scoped to visual artifact agents only. Opus is reserved for `anchor` (evidence-first verification) and `architect` (system design).

### Key Agent Roles

| Agent | Role |
|-------|------|
| **Orchestrator** | Pipeline brain — reads `pipeline-state.json`, validates artefact contracts, routes to next agent. Never writes code. |
| **Anchor** | Evidence-first implementation — captures baseline, verifies every deliverable exists with grep proof, applies Partial Completion Protocol when context runs low |
| **Architect** | System design, ADR authoring, diagrams. Writes ADRs to `docs/architecture/agentic-adr/ADR-{feature-slug}.md` |
| **Plan** | Breaks approved architecture into phased implementation plans in `.github/plans/` |
| **PRD** | Captures requirements into a formal PRD document |
| **Implement** | Writes production code following the plan |
| **Tester / Code Reviewer / Debug / Security Analyst** | Quality gates at various pipeline stages |
| **Knowledge Transfer** | Institutional memory — extracts durable knowledge from completed sessions and writes to `docs/gold-nuggets-log.md` and instruction files |
| **Janitor** | Housekeeping — archives stale artefacts, removes dead code |

---

## The Pipeline Flow

```
Intent → PRD → Architecture/ADR → Plan → Implement → Test → Review → (Security) → Done
```

Each stage is gated. Gates are stored in `.github/pipeline-state.json`. The Orchestrator reads the state, satisfies gates (manually in supervised mode, automatically in autopilot mode), and routes to the next agent.

### Pipeline Modes
- **supervised** — All gates require manual approval (recommended)
- **assisted** — Manual gates with AI guidance hints
- **autopilot** — All gates auto-satisfied except `intent_approved`

### Auto-Routing and Pipeline State
VS Code Copilot can invoke named agents automatically without a button click. **This does not bypass pipeline gates** — enforcement is via `pipeline-state.json` + MCP `satisfy_gate` calls, not button clicks. However, auto-routing from **outside the pipeline** (i.e. from default Copilot chat rather than from Orchestrator) will not update `pipeline-state.json` and causes state desync. Always enter the pipeline via `@Orchestrator`. See `advisory-mode.instructions.md` for the full boundary rule.

**Routing mechanism:** In `assisted` and `autopilot` modes, agents trigger routing by writing `@AgentName [prompt]` as the final line of their response. VS Code picks up the `@AgentName` reference and auto-invokes that agent. Handoff buttons (`send: false`) are only used for supervised-mode approval clicks — they are never auto-clicked by any automation.

**How it works per mode:**
- `supervised` — Orchestrator shows handoff button; user clicks = approval. Specialist shows Return button; user clicks to start next cycle.
- `assisted` — Orchestrator writes `@[AgentName] [routing prompt]` as its final line; VS Code auto-invokes the specialist. Specialist writes `@Orchestrator Stage complete — [summary]...` when done; VS Code auto-invokes Orchestrator. Stops only at supervision gates.
- `autopilot` — Identical to assisted routing; additionally, most supervision gates are auto-satisfied. Fully hands-free loop after `intent_approved`.

### VS Code Autopilot Integration
VS Code introduced a distinct **Autopilot permission level** (Chat view permissions picker, preview) that auto-approves all tool calls, auto-retries errors, and auto-responds to blocking clarification questions. This is separate from junai's `pipeline_mode: autopilot`.

**The two autopilot concepts are complementary, not competing:**

| Layer | Scope | Controls |
|-------|-------|----------|
| **VS Code Autopilot** (permission level) | Runtime tool execution | Auto-approves tool calls, auto-retries MCP errors, auto-responds to blocking questions |
| **junai `pipeline_mode: autopilot`** (state machine) | Pipeline orchestration | Stage routing, artefact contracts, gate enforcement, model-per-specialist, cross-session continuity |

**For fully hands-free pipeline runs**, enable both:
1. VS Code Chat → permissions picker → **Autopilot (Preview)**
2. Set `"pipeline_mode": "autopilot"` in `.github/pipeline-state.json`

With both enabled: `@Orchestrator` reads state → writes `@Specialist [routing prompt]` → VS Code invokes specialist → specialist calls MCP tools (auto-approved) → specialist writes `@Orchestrator Stage complete — [summary]...` → VS Code invokes Orchestrator → repeat.

### Key Pipeline Conventions
- `chain_id` format: `FEAT-YYYY-MMDD-{slug}` — links all artefacts for a feature
- Artefacts in `agent-docs/` are **transient** (inter-agent working space, not project docs)
- Artefacts in `docs/` are **permanent** (canonical project documentation)
- ADR path: `docs/architecture/agentic-adr/ADR-{feature-slug}.md` (pipeline-produced ADRs, not manually authored docs)
- Plans live in `.github/plans/` and are referenced from `agent-docs/ARTIFACTS.md`

---

## The MCP Server

`.github/tools/mcp-server/server.py` is a **FastMCP server** that runs over stdio. It provides 9 tools to all agents:

| Tool | Purpose |
|------|---------|
| `get_pipeline_status` | Read current pipeline-state.json |
| `notify_orchestrator` | Write routing decisions / notes to state |
| `pipeline_init` | Initialise a new pipeline run |
| `pipeline_reset` | Reset state for a new feature |
| `satisfy_gate` | Mark a pipeline gate as satisfied |
| `set_pipeline_mode` | Switch supervised/assisted/autopilot |
| `skip_stage` | Skip a stage with a reason |
| `validate_deferred_paths` | Check if deferred artefact paths now exist |
| `run_command` | Execute shell commands from within agent context |

The server is registered in `.vscode/mcp.json` as `junai` and uses `${workspaceFolder}/.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Linux/Mac).

> **Critical fix (v0.4.9):** All subprocess spawns in `server.py` use `stdin=asyncio.subprocess.DEVNULL` to prevent MCP stdio pipe inheritance deadlock.

---

## Publish Workflow

### Standard publish (after editing agents/skills/instructions):

```powershell
# 1. Validate all 25 agents + MCP smoke test
cd E:\Projects\agent-sandbox
.venv\Scripts\python.exe validate_agents.py

# 2. Commit to agent-sandbox (local only)
git add .github/...; git commit -m "feat: ..."

# 3. Bump version and publish VS Code extension
cd E:\Projects\junai-vscode
# Edit package.json version manually
git add package.json; git commit -m "chore: bump version to X.Y.Z"
$env:VSCE_PAT = (Get-Content "vscode.pat" -Raw).Trim()
npm run publish   # runs bundle-pool + compile + vsce publish
git push

# 4. Sync public pool mirror
cd E:\Projects\junai
git add .github/agents .github/skills .github/prompts .github/instructions .github/diagrams .github/tools
git commit -m "feat: sync pool from agent-sandbox - YYYY-MM-DD"
git push
```

### What `npm run publish` does internally:
1. `bundle-pool.js` — wipes `pool/`, copies `.github/` folders from agent-sandbox, skips `vmie` skill, guards against `dir/dir` accidental nesting, writes `POOL_VERSION` from `package.json`
2. `tsc` — compiles `src/extension.ts` → `out/extension.js`
3. `vsce publish` — packages and uploads to marketplace

---

## validate_agents.py

Pre-publish gate at `E:\Projects\agent-sandbox\validate_agents.py`. Checks all 25 agents for:
- Required frontmatter fields (`name`, `model`, `tools`, `description`)
- Model is in the known allowlist (`KNOWN_MODELS`)
- Presence of `## §8` and `## §9` sections (or equivalent)
- Partial Completion Protocol present in §8
- MCP smoke test: starts `server.py`, sends JSON-RPC `initialize` + `tools/list`, verifies 9 tools respond

Run before every publish — `npm run publish` does **not** run it automatically; it is the human's responsibility to run it first.

---

## Key Conventions

### Agent File Structure (`.agent.md`)
```yaml
---
name: <Agent Name>
description: <one-line purpose>
model: <Model Name>
tools: [tool1, tool2, ...]
handoffs:
  - label: <Button label>
    agent: <Target Agent Name>
    prompt: <Routing prompt>
    send: false
---
```
Followed by behavioral instructions using a consistent section structure: §1 Role, §2 Input, §3–7 task-specific phases, §8 Protocols (HARD STOP, Partial Completion), §9 Output Contract.

### Partial Completion Protocol (all agents, §8)
If an agent runs out of context or token budget mid-task:
1. Stop immediately — do not attempt to compress or rush
2. Commit whatever stable work exists
3. Report honestly: what is DONE vs what is NOT DONE
4. Do NOT mark the pipeline stage as complete
5. User resumes with a fresh session

### Artefact Registry (`.github/agent-docs/ARTIFACTS.md`)
All inter-agent artefacts are registered here. Status values: `current` | `superseded` | `archived` | `completed`. Always check this before reading any artefact — only read `current` entries.

### Instructions Files
`.github/instructions/*.instructions.md` files have `applyTo` frontmatter globs. They define coding conventions (Python, SQL, security, accessibility, performance, etc.) and are applied automatically by VS Code Copilot to matching file patterns.

---

## VS Code Extension Behaviour

When a user installs `junai-labs.junai` and runs **Initialize**:
- Copies the entire pool (`agents/`, `skills/`, `prompts/`, `instructions/`, `agent-docs/`, `plans/`, `handoffs/`, `tools/`) into the project's `.github/` folder
- Creates `.github/pipeline-state.json`
- Writes `.vscode/mcp.json` registering the MCP server
- Stamps `.github/.junai-pool-version` with the current pool version

On every VS Code activation, `checkPoolUpdate` compares the bundled pool version against the workspace's stamped version. If they differ, it silently runs `cmdUpdate` which:
1. Auto-heals any `dir/dir` nested folders (legacy bug from v0.5.1 and earlier)
2. Merges updated pool files into the workspace (skips `pipeline-state.json` and `project-config.md` — user-owned)

---

## What NOT to Do in This Workspace

- Do NOT add application code here — this is infrastructure/tooling only
- Do NOT commit secrets or PAT tokens (`.vscode.pat` is gitignored)
- Do NOT run `git push` from agent-sandbox — it has no remote
- Do NOT edit files in `E:\Projects\junai-vscode\pool\` directly — they are wiped and regenerated on every `npm run publish`
- Do NOT skip `validate_agents.py` before publishing
