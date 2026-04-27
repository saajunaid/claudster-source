---
description: "junai agent pipeline system documentation — 25 agents, MCP tools, pipeline flow, routing conventions. Pool-managed: refreshed on every junai update."
applyTo: "**"
---

# junai Agent Pipeline — System Reference

This file is deployed and maintained by the junai VS Code extension. It is refreshed automatically when you run **Update Agent Pool** — do not edit it by hand. For project-specific context, edit `.github/copilot-instructions.md` instead (the extension manages only a small `<!-- junai:start -->` … `<!-- junai:end -->` section there; your content outside the markers is never touched).

---

## The 25 Agents

Each agent lives in `.github/agents/<name>.agent.md`. Each has a YAML frontmatter block with `name`, `model`, `tools`, `handoffs`, and `description`, followed by detailed behavioral instructions.

### Model Assignments

| Model | Agents |
|-------|--------|
| Claude Opus 4.6 | `anchor`, `architect` — highest-rigor work |
| Claude Sonnet 4.6 | `orchestrator`, `planner`, `prd`, `prompt-engineer`, `security-analyst`, `accessibility`, `code-reviewer`, `debug`, `mentor`, `project-manager`, `ux-designer`, `ui-ux-designer`, `knowledge-transfer` |
| GPT-5.3-Codex | `implement`, `streamlit-developer`, `frontend-developer`, `data-engineer`, `devops`, `janitor`, `sql-expert`, `tester` |
| Gemini 3.1 Pro (Preview) | `mermaid-diagram-specialist`, `svg-diagram` — visual artifact generation only |

### Key Agent Roles

| Agent | Role |
|-------|------|
| **Orchestrator** | Pipeline brain — reads `pipeline-state.json`, validates artefact contracts, routes to next agent. Never writes code. |
| **Anchor** | Evidence-first implementation — captures baseline, verifies every deliverable exists with grep proof, applies Partial Completion Protocol when context runs low |
| **Architect** | System design, ADR authoring, diagrams. Writes ADRs to `docs/architecture/agentic-adr/ADR-{feature-slug}.md` |
| **Planner** | Breaks approved architecture into phased implementation plans in `.github/plans/` |
| **PRD** | Captures requirements into a formal PRD document |
| **Implement** | Writes production code following the plan |
| **Tester / Code Reviewer / Debug / Security Analyst** | Quality gates at various pipeline stages |
| **Knowledge Transfer** | Institutional memory — extracts durable knowledge from completed sessions and writes to `docs/gold-nuggets-log.md` and instruction files |
| **Janitor** | Housekeeping — archives stale artefacts, removes dead code |

---

## The Pipeline Flow

```
Intent → PRD → Architecture/ADR → Planner → Implement → Test → Review → (Security) → Done
```

Each stage is gated. Gates are stored in `.github/pipeline-state.json`. The Orchestrator reads the state, satisfies gates (manually in supervised mode, automatically in autopilot mode), and routes to the next agent.

### Pipeline Modes
- **supervised** — All gates require manual approval (recommended)
- **assisted** — Manual gates with AI guidance hints
- **autopilot** — All gates auto-satisfied except `intent_approved`

**Always enter the pipeline via `@Orchestrator`.** Auto-routing from default Copilot chat bypasses `pipeline-state.json` updates and causes state desync. See the `advisory-mode.instructions.md` boundary rule for details.

### Auto-Routing Mechanism

In `assisted` and `autopilot` modes, agents trigger routing by writing `@AgentName [prompt]` as the **final line** of their response. VS Code picks up the `@AgentName` reference and auto-invokes that agent. Handoff buttons (`send: false`) are only used for supervised-mode approval clicks — they are never auto-clicked by any automation.

**Per mode:**
- `supervised` — Orchestrator shows handoff button; user clicks = approval.
- `assisted` — Orchestrator writes `@[AgentName] [routing prompt]` as its final line; VS Code auto-invokes specialist. Specialist writes `@Orchestrator Stage complete — [summary]. Read pipeline-state.json and _routing_decision, then route.` when done.
- `autopilot` — Identical to assisted; additionally, most supervision gates are auto-satisfied. Fully hands-free loop after `intent_approved`.

### VS Code Autopilot Integration

VS Code's **Autopilot permission level** (Chat view permissions picker, preview) and junai's **`pipeline_mode: autopilot`** are complementary layers:

| Layer | Scope | Controls |
|-------|-------|----------|
| **VS Code Autopilot** (permission level) | Runtime tool execution | Auto-approves tool calls, auto-retries MCP errors, auto-responds to blocking questions |
| **junai `pipeline_mode: autopilot`** (state machine) | Pipeline orchestration | Stage routing, artefact contracts, gate enforcement, model-per-specialist |

For fully hands-free runs: enable VS Code Chat → permissions picker → **Autopilot (Preview)** AND set `"pipeline_mode": "autopilot"` in `.github/pipeline-state.json`.

---

## The 9 MCP Tools

The MCP server at `.github/tools/mcp-server/server.py` is launched via `uv run` (PEP 723 inline deps — `fastmcp` installs automatically on first start, no `pip install` needed).

| Tool | Purpose |
|------|---------|
| `get_pipeline_status` | Read current stage, mode, routing decision |
| `notify_orchestrator` | Record stage completion + trigger routing decision |
| `pipeline_init` | Initialise a new pipeline run (active-pipeline guard built-in) |
| `pipeline_reset` | Force-clear and restart (bypasses guard) |
| `satisfy_gate` | Manually satisfy a supervision gate |
| `set_pipeline_mode` | Switch supervised / assisted / autopilot |
| `skip_stage` | Skip current stage with a reason (unskippable on implement/anchor/tester) |
| `validate_deferred_paths` | Verify deferred artefact file paths exist |
| `run_command` | Execute CLI commands from chat context |

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
Followed by sections §1 Role, §2 Input, §3–7 task phases, §8 Protocols (HARD STOP, Partial Completion), §9 Output Contract.

### Artefact Registry (`.github/agent-docs/ARTIFACTS.md`)
All inter-agent artefacts are registered here. Status values: `current` | `superseded` | `archived` | `completed`. Always check this before reading any artefact — only read `current` entries.

### Artefact Locations
- `chain_id` format: `FEAT-YYYY-MMDD-{slug}` — links all artefacts for a feature
- `agent-docs/` — **transient** inter-agent working space (not project docs)
- `docs/` — **permanent** canonical project documentation
- ADR path: `docs/architecture/agentic-adr/ADR-{feature-slug}.md`
- Plans: `.github/plans/<feature-slug>.md`

### Git Commit Convention (all agents)
When making a git commit at stage completion, always stage `.github/pipeline-state.json` explicitly alongside the code changes. This keeps pipeline state in sync with git history so that `git reset --hard` restores both atomically.

### Partial Completion Protocol (all agents, §8)
If an agent runs out of context or token budget mid-task:
1. Stop immediately — do not attempt to compress or rush
2. Commit whatever stable work exists (include `.github/pipeline-state.json`)
3. Report honestly: what is DONE vs what is NOT DONE
4. Do NOT mark the pipeline stage as complete
5. User resumes with a fresh session

### Instructions Files
`.github/instructions/*.instructions.md` files define coding conventions (Python, SQL, FastAPI, security, accessibility, performance, etc.) and are applied automatically by VS Code Copilot to matching files based on `applyTo` patterns.
