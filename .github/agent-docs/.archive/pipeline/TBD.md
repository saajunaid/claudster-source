# User Guide — Notes (To Be Written)

> This file is a structured outline of everything that must be covered in the final README / User Guide before public release.
> Do NOT write the guide from this file alone — validate against the actual implementation first.

---

## 1. What It Is

- One-paragraph plain-English description: "An agent pipeline infrastructure for VS Code + GitHub Copilot that routes work between specialised AI agents in a deterministic, auditable way."
- Key differentiators vs raw Copilot chat:
  - Deterministic routing (state machine, not LLM inference)
  - Persistent pipeline state across sessions
  - Three pipeline modes: supervised, assisted, autopilot
  - Auditable artefacts with approval frontmatter
  - Plug-and-play agent onboarding

---

## 2. Prerequisites

- VS Code (version minimum — confirm)
- GitHub Copilot extension with agent/tool support enabled
- Python 3.11+ on PATH
- Git

---

## 3. Installation & Setup

### 3a. Clone / copy the agent pool
- Where the files live, folder structure overview
- `.github/agents/`, `tools/`, `.vscode/mcp.json`, `skills/`, `instructions/`

### 3b. Create the virtual environment
```powershell
python -m venv .venv
.venv\Scripts\pip install -r tools/mcp-server/requirements.txt
.venv\Scripts\pip install -r tools/pipeline-runner/requirements.txt
```

### 3c. Register the MCP server
- VS Code reload after venv is created
- How to verify tools appear in Copilot chat (tools icon)
- Expected tools (5 total): `notify_orchestrator`, `validate_deferred_paths`, `get_pipeline_status`, `set_pipeline_mode`, `satisfy_gate`

### 3d. Initialise a pipeline
Use the CLI wrapper (no Python path required):
```powershell
# Windows
pipeline init --project <project-name> --feature <feature-slug> --type feature

# Mac/Linux
./pipeline.sh init --project <project-name> --feature <feature-slug> --type feature
```
Or from anywhere using the full path:
```powershell
.venv\Scripts\python tools/pipeline-runner/pipeline_runner.py init --project <name> --feature <slug> --type feature|hotfix
```
This copies `pipeline-state.template.json`, sets `project`, `feature`, `type`, `pipeline_mode: supervised`, and writes `.github/pipeline-state.json`.

> **Note:** `init` is CLI-only intentionally — see Design Decision in §19 below.

---

## 4. Pipeline Mode

Pipeline mode is set per-pipeline and controls whether the user manually triggers each agent handoff or the orchestrator fires them automatically.

**Switch mode — three options:**
1. CLI: `pipeline mode --value supervised`, `pipeline mode --value assisted`, or `pipeline mode --value autopilot`
2. MCP (natural language in Copilot chat): *"Switch pipeline to assisted mode"* → calls `set_pipeline_mode` tool
3. Direct JSON edit: set `pipeline_mode` in `pipeline-state.json` (fallback)

> Default is always `supervised`. `assisted` / `autopilot` are explicit opt-ins.

### In the guide, cover:
- What supervised mode does (routing presented as handoff button, user clicks to proceed)
- What `assisted` mode does (orchestrator invokes next agent immediately; gates still require user approval)
- What `autopilot` mode does (orchestrator auto-routes; most gates auto-satisfied except `intent_approved`)
- That gates (`plan_approved`, `adr_approved`, `review_approved`, `intent_approved`) are **never bypassed** in supervised or assisted mode
- That blocked/escalation states always surface to the user in all modes
- Recommended default: `supervised` (safe for first-time users)

---

## 5. Stages & Agents Reference

Full table of all 16 stages with:
- Stage name (as it appears in `pipeline-state.json`)
- Agent that handles it
- Agent file path
- Brief one-line description of what the agent does
- Source: `agents.registry.json` → `stages`

---

## 6. Transitions Reference (T-01 – T-27)

Short table of all transitions with:
- ID
- From → To
- Triggering event
- Guards required
- Gate (if any)
- Hotfix only flag
- Source: `agents.registry.json` → `transitions`

---

## 7. Gates — What They Are & How to Satisfy Them

- Explain gate concept: a stage that requires explicit human approval before advancing
- List the 4 current gates: `intent_approved`, `adr_approved`, `plan_approved`, `review_approved`
- How to mark a gate satisfied — three options:
  1. CLI: `pipeline gate --name intent_approved`
  2. MCP (natural language in Copilot chat): *"Approve intent_approved"* → calls `satisfy_gate` tool
  3. Direct JSON edit: set `"intent_approved": true` under `supervision_gates` in `pipeline-state.json`
- Gates are **never auto-bypassed** regardless of `pipeline_mode`

---

## 8. MCP Tools Reference

### `get_pipeline_status`
- No parameters
- Returns: current stage, mode, project name, last updated
- When to use: anytime you want a quick status snapshot

### `notify_orchestrator`
- Parameters: `stage_completed`, `result_status`, `artefact_path` (optional), `result_payload` (optional)
- Returns: computed next transition, next stage, gate status, blocking reason if any
- When agents call it: at the end of every stage completion (§8 Completion Reporting Protocol)

### `validate_deferred_paths`
- Parameters: `deferred_items` (list)
- Returns: validation result per item
- When to use: before closing a pipeline when deferred items exist

### `set_pipeline_mode`
- Parameters: `mode` (`supervised` | `assisted` | `autopilot`)
- Returns: confirmation of updated mode
- When to use: changing pipeline mode mid-run; natural language → *"Switch to assisted mode"*

### `satisfy_gate`
- Parameters: `gate_name` (`intent_approved` | `adr_approved` | `plan_approved` | `review_approved`)
- Returns: confirmation of gate satisfied
- When to use: approving a gate in Copilot chat; natural language → *"Approve plan_approved"*

> All 5 tools are accessible via natural language in Copilot chat — the tools icon shows them active.

---

## 9. CLI Reference

Wrapper scripts at workspace root (recommended — no Python path needed):
```powershell
# Windows
pipeline <command>

# Mac/Linux
./pipeline.sh <command>
```

Or directly:
```powershell
.venv\Scripts\python tools/pipeline-runner/pipeline_runner.py <command>
```

| Command | What it does |
|---|---|
| `status` | Print current stage, mode, last updated |
| `next --event <event>` | Compute next transition without writing state |
| `advance --event <event>` | Compute AND write next transition to state file |
| `preflight` | Validate state file structure and coverage requirements |
| `mode --value supervised\|assisted\|autopilot` | Switch pipeline mode |
| `gate --name <gate_name>` | Mark a supervision gate as satisfied |
| `init --project <name> --feature <slug> [--type feature\|hotfix] [--force]` | Initialise or reset pipeline state |
| `transitions` | Print all T-01–T-27 transitions as a table |

---

## 10. Adding a New Agent to the Pipeline

This is the "plug-and-play" section — the key selling point.

Steps:
1. Add a `stages` entry in `agents.registry.json`
2. Add `transitions` entries in `agents.registry.json`
3. Write the `.agent.md` with §8 Completion Reporting Protocol + HARD STOP
4. No Python changes, no restart

Include a worked example (e.g., adding a `data-engineer` stage between `plan` and `implement`).

---

## 11. Adding Ad-Hoc Agents (Not Pipeline-Integrated)

- Just create the `.agent.md` — no registry, no transitions needed
- These are called by humans on demand, not by the orchestrator
- Should still have §8 for consistency if auto-mode is ever desired

---

## 12. Adding Skills, Prompts, Instructions

- Fully plug-and-play today
- Skills: create file + add entry to `skills/_registry.md`
- Prompts: create file in `prompts/`
- Instructions: create file in `instructions/`
- Reference them inside an agent's `load:` block

---

## 13. Hotfix Workflow

- How hotfix pipelines differ from feature pipelines
- Set `type: hotfix` and `hotfix_id` in `pipeline-state.json`
- Hotfix-only transitions (T-17 to T-22): intake → debug → implement → tester → closed (or review if security deferrals)
- No PRD / Architect / Plan stages

---

## 14. Blocked State & Recovery

- What causes a BLOCKED state (escalation with `severity: blocking`)
- Where escalation files live (`agent-docs/escalations/`)
- How to recover: resolve the root cause, clear `blocked_by` in state, set `status: resolved` on escalation file
- T-27 transition: BLOCKED → recovered

---

## 15. Deferred Items & Re-entry

- What deferred items are (work intentionally skipped during a pipeline run)
- How they're recorded in `pipeline-state.json` → `deferred[]`
- T-23 transition: closed → implement for deferred re-entry
- `validate_deferred_paths` MCP tool to check if deferred artefacts now exist

---

## 16. `pipeline-state.json` Schema Reference

Full field-by-field reference including:
- `pipeline_mode`, `type`, `hotfix_id`
- `current_stage`, `status`, `gates`
- `stages{}` per-stage objects
- `deferred[]` items
- `_notes.handoff_payload`, `_notes._routing_decision`
- Template location: `.github/pipeline-state.template.json`

---

## 17. Project Config

- `project-config.md` — what it contains, why agents load it
- `copilot-instructions.md` — workspace-level agent context

---

## 18. Troubleshooting

- MCP tools don't appear → venv not created or VS Code not reloaded; run `python -m venv .venv` and reload window
- `get_pipeline_status` returns empty → `PIPELINE_STATE_PATH` env var wrong in `.vscode/mcp.json`; must be absolute path to `pipeline-state.json`
- Transition computes wrong stage → run `pipeline next --event <event>` in terminal to debug without writing state
- Agent ignores HARD STOP → check §8 Completion Reporting Protocol is present in the agent file
- Gate never satisfied in supervised/assisted mode → gates always require manual approval in these modes; use `pipeline gate --name <gate_name>` or say *"Approve <gate_name>"* in Copilot chat
- `pipeline` command not found → `pipeline.bat` must be in workspace root; confirm with `Test-Path pipeline.bat`
- Pipeline state looks wrong after direct agent work → run Orchestrator and it will run §9.2 drift resync automatically

---

## 19. Shipped UX Improvements (Phase 5 — complete)

All items below shipped in Phase 5 (`DeterministicRouting.md` 5a–5g). No workarounds needed.

| Capability | CLI | MCP (natural language) |
|---|---|---|
| Switch pipeline mode | `pipeline mode --value supervised|assisted|autopilot` | *"Switch to assisted mode"* → `set_pipeline_mode` |
| Satisfy gates | `pipeline gate --name <gate_name>` | *"Approve plan_approved"* → `satisfy_gate` |
| Init new pipeline | `pipeline init --project <n> --feature <s> [--type] [--force]` | CLI only (intentional — see below) |
| View transition table | `pipeline transitions` | — |

### Design Decision — `init` intentionally NOT an MCP tool

`set_pipeline_mode` and `satisfy_gate` are safe as MCP tools because they make reversible, non-destructive edits to an existing state file.

`init` is **deliberately CLI-only** because:
- It destroys and recreates `pipeline-state.json`
- A careless natural-language prompt mid-run (e.g. "start a new pipeline") could silently wipe live state
- The CLI requires explicit deliberate invocation

**Future path (VS Code command palette integration):** If `init` is ever promoted to an MCP tool it must include:
- `confirm_overwrite: bool = False` parameter — refuse silently if state file exists unless explicitly set
- Or a VS Code confirmation dialog in the command palette integration

Do not add `init` as an MCP tool without this safeguard.
