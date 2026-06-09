# Deterministic Routing — Design Review

**Date:** 2025-02-21
**Author:** Architect Agent
**Scope:** GAP-H5 / GAP-I2 — Replace LLM-inferred routing with a deterministic Python state machine
**Status:** Design review — no implementation yet

---

## Table of Contents

1. [Task 1 — Transition Table Review](#task-1--transition-table-review)
2. [Task 2 — File Structure Design](#task-2--file-structure-design)
3. [Task 3 — Orchestrator Agent Changes](#task-3--orchestrator-agent-changes)
4. [Task 4 — Updated Implementation Order](#task-4--updated-implementation-order)
5. [Risks & Open Questions](#risks--open-questions)

---

## Task 1 — Transition Table Review

### 1.1 Methodology

The transition table below was derived by exhaustive reading of:
- `orchestrator.agent.md` §3 (Routing Logic), §9 (Intake), §10 (Close), §11 (Tester Retry), §12 (Hotfix)
- `pipeline-state SKILL.md` (schema, handoff_payload, pipeline_mode)
- `pipeline-state.template.json` (canonical stage names)
- All 9 agents with `Return to Orchestrator` + HARD STOP completion protocols
- All agent `Output Contract` sections (next_agent fields)

### 1.2 Canonical Stage Names

From the template and orchestrator routing logic, the canonical stages are:

| Stage Key | Agent(s) | Notes |
|-----------|----------|-------|
| `intent` | (user / orchestrator) | User writes intent; orchestrator validates |
| `prd` | PRD | |
| `architect` | Architect | |
| `security` | Security Analyst | Parallel with architect (plan-defined) |
| `plan` | Plan | |
| `ux_research` | UX Designer | Optional UI track |
| `ui_design` | UI/UX Designer | Optional UI track |
| `implement` | Implement, Streamlit Dev, Frontend Dev, Data Engineer, SQL Expert | Multi-agent, plan assigns |
| `tester` | Tester | |
| `review` | Code Reviewer | |
| `debug` | Debug | Support, not main pipeline |
| `devops` | DevOps | Support |
| `janitor` | Janitor | Support |
| `closed` | — | Terminal state |

### 1.3 Complete Transition Table

```
Legend:
  FROM             → TO               GUARD                              GATE           MODE
  (current_stage)    (next_stage)     (condition that must be true)      (supervision)  (supervised|auto|both)
```

#### Main Pipeline (happy path)

| # | FROM | TO | GUARD | GATE | MODE |
|---|------|----|-------|------|------|
| T-01 | `intent` | `prd` | intent artefact exists | `intent_approved` | both |
| T-02 | `prd` | `architect` | PRD artefact exists, `approval: approved` | — | both |
| T-03 | `architect` | `plan` | Architecture artefact exists, `approval: approved` | `adr_approved` | both |
| T-04 | `plan` | `implement` | Plan artefact exists, `approval: approved` | `plan_approved` | both |
| T-05 | `implement` | `tester` | Implementation committed, `current_phase == total_phases` | — | both |
| T-06 | `tester` | `review` | `tester_result.status == passed` | — | both |
| T-07 | `review` | `closed` | `approval: approved`, no deferred security items | `review_approved` | both |

#### Parallel Branches (plan-defined)

| # | FROM | TO | GUARD | GATE | MODE |
|---|------|----|-------|------|------|
| T-08 | `architect` | `security` | Plan defines parallel security review | — | both |
| T-09 | `security` | `plan` | Security artefact `approval: approved` AND architect `status: complete` | `adr_approved` | both |
| T-10 | `plan` | `ux_research` | Plan defines UI track | — | both |
| T-11 | `ux_research` | `ui_design` | UX research artefact exists | — | both |
| T-12 | `ui_design` | `implement` | UI/UX spec exists, `approval: approved` | `plan_approved` | both |

#### Multi-Phase Implementation Loop

| # | FROM | TO | GUARD | GATE | MODE |
|---|------|----|-------|------|------|
| T-13 | `implement` | `implement` | `current_phase < total_phases` (next phase) | — | both |

#### Tester Retry Loop

| # | FROM | TO | GUARD | GATE | MODE |
|---|------|----|-------|------|------|
| T-14 | `tester` | `implement` | `tester_result.status == failed` AND `retry_count < max_retries` | — | both |
| T-15 | `tester` | `BLOCKED` | `tester_result.status == failed` AND `retry_count >= max_retries` | — | both |

#### Review Feedback Loop

| # | FROM | TO | GUARD | GATE | MODE |
|---|------|----|-------|------|------|
| T-16 | `review` | `implement` | `approval: revision-requested` | — | both |

#### Hotfix Mini-Pipeline

| # | FROM | TO | GUARD | GATE | MODE |
|---|------|----|-------|------|------|
| T-17 | `intake` | `debug` | Unknown root cause, `type: hotfix` | — (all gates auto-approved) | both |
| T-18 | `intake` | `implement` | Known root cause, `type: hotfix` | — (all gates auto-approved) | both |
| T-19 | `debug` | `implement` | Debug report `approval: approved` | — | both |
| T-20 | `implement` | `tester` | Hotfix committed (hotfix path, no phase check) | — | both |
| T-21 | `tester` | `review` | `tester_result.status == passed` AND any deferred item has `severity ∈ {security-nit, security}` | — | both |
| T-22 | `tester` | `closed` | `tester_result.status == passed` AND no security deferrals | — | both |

#### Deferred Re-Entry

| # | FROM | TO | GUARD | GATE | MODE |
|---|------|----|-------|------|------|
| T-23 | `closed` | `implement` | `deferred[]` is non-empty, user requests re-entry | — (all gates auto-approved) | both |

#### Pipeline Mode Branching

| # | FROM | TO | GUARD | GATE | MODE |
|---|------|----|-------|------|------|
| T-24 | (any) | (next per table) | `pipeline_mode == "auto"` | Gates still checked, but NO user prompt — auto-proceed | auto only |
| T-25 | (any) | (next per table) | `pipeline_mode == "supervised"` | Present handoff button, WAIT for user click | supervised only |

#### Blocked State Transitions

| # | FROM | TO | GUARD | GATE | MODE |
|---|------|----|-------|------|------|
| T-26 | (any) | `BLOCKED` | Artefact missing, approval missing, escalation `severity: blocking` | — | both |
| T-27 | `BLOCKED` | (previous stage) | `blocked_by` cleared by user, artefact/approval fixed | — | both |

### 1.4 Gaps & Missing Branches Identified

#### GAP-T1: `pipeline_mode` not in template JSON

**Finding:** `pipeline_mode` is referenced in `pipeline-state/SKILL.md` (line 179) but is **absent from `pipeline-state.template.json`**. New pipelines silently default to `undefined` rather than `"supervised"`.

**Fix:** Add `"pipeline_mode": "supervised"` to the root of `pipeline-state.template.json`.

#### GAP-T2: PRD, Architect, Debug, Security Analyst lack Completion Protocol

**Finding:** Only 9 agents have the `Return to Orchestrator` handoff + `HARD STOP` + Completion Reporting Protocol (§8). The following main-pipeline agents **do not**:

| Agent | Pipeline Stage | Has Return Handoff | Has HARD STOP |
|-------|---------------|-------------------|---------------|
| PRD | `prd` | ❌ | ❌ |
| Architect | `architect` | ❌ | ❌ |
| Debug | `debug` | ❌ | ❌ |
| Security Analyst | `security` | ❌ | ❌ |
| UX Designer | `ux_research` | ❌ | ❌ |
| UI/UX Designer | `ui_design` | ❌ | ❌ |

**Risk:** In auto mode, these agents will complete their work but `pipeline-runner` has no structured completion signal to detect. The human must manually resume routing.

**Fix (Phase 4):** Add Completion Reporting Protocol §8 + `Return to Orchestrator` handoff to all 6 agents. For Phase 1-2, pipeline-runner should treat these stages as `supervised`-only until the agents are updated.

#### GAP-T3: Parallel stage tracking — no schema support

**Finding:** `pipeline-state.json` has a flat `stages` map — one status per stage. When architect and security-analyst run in parallel (T-08/T-09), there is no way to track both as `in_progress` simultaneously and wait for both to complete before transitioning to `plan`.

**Fix:** Add `parallel_group` support to `pipeline-state.json`:
```json
{
  "parallel_groups": {
    "arch_security": {
      "stages": ["architect", "security"],
      "join_to": "plan",
      "completed": []
    }
  }
}
```

The pipeline-runner checks: transition fires to `join_to` only when `completed == stages`. Otherwise each completing stage marks itself done and the runner waits.

**Deferral recommendation:** Parallel stages are plan-defined and rare. For Phase 1-2, the runner can support only sequential transitions. Add parallel support in a follow-up.

#### GAP-T4: Hotfix security gate condition is ambiguous

**Finding:** Orchestrator §12 says: *"If ANY deferred item has `severity: security-nit`, `security`, or higher — route to `@code-reviewer` after tester passes."* But `deferred[]` is populated by code-reviewer, which hasn't run yet in a hotfix. The deferred items from a **previous** pipeline close are what trigger this.

**Clarification needed:** The check should be: scan `pipeline-state.json deferred[]` (from the originating closed pipeline) — if any item being fixed has `severity ∈ {security-nit, security}`, then `tester → review` instead of `tester → closed`. The transition table T-21/T-22 above reflects this corrected interpretation.

#### GAP-T5: `implement` stage — multi-agent routing ambiguity

**Finding:** The `implement` stage can be served by 5 different agents (Implement, Streamlit Dev, Frontend Dev, Data Engineer, SQL Expert). The pipeline-runner needs to know WHICH agent to route to — this is in the plan's agent_assignments but not currently in `pipeline-state.json`.

**Fix:** The orchestrator (LLM) reads the plan and writes `_notes.handoff_payload.target_agent` before routing. The pipeline-runner just uses this value from the state file. This already exists in the schema — just needs enforcement.

#### GAP-T6: No transition for `architect → plan` when security is NOT parallel

**Finding:** T-03 covers `architect → plan` with the `adr_approved` gate. T-09 covers the parallel case where security must also complete. But there's no explicit branch condition for "is security parallel or not?".

**Fix:** The pipeline-runner checks: if `parallel_groups` contains an active group with `architect` as a member, use the parallel join logic (T-09). Otherwise, use the simple transition (T-03). Since we're deferring parallel support (GAP-T3), T-03 is the only path for Phase 1-2.

#### GAP-T7: No `intake` pseudo-stage in the schema

**Finding:** The orchestrator's Intake Protocol (§9) classifies the user's initial request and sets the starting stage. This is currently LLM-driven. For deterministic routing, this is one of the things we **keep as LLM-driven** — the pipeline-runner should not attempt to classify natural language requests.

**Design decision:** `intake` is NOT a pipeline-runner transition. It stays as an orchestrator LLM responsibility. The orchestrator writes the classified starting state to `pipeline-state.json`, and from that point forward `pipeline-runner` owns all transitions.

---

## Task 2 — File Structure Design

### 2.1 Directory Layout

```
tools/
├── mcp-server/
│   ├── server.py              # FastMCP server: notify_orchestrator + validate_deferred_paths
│   ├── requirements.txt       # fastmcp, pydantic
│   └── README.md              # Usage instructions for MCP server
├── pipeline-runner/
│   ├── pipeline_runner.py     # CLI entry point: reads state, computes transition, writes state
│   ├── transitions.py         # Transition table as data + guard evaluator
│   ├── schema.py              # Pydantic models for pipeline-state.json
│   ├── guards.py              # Guard condition implementations (file exists, YAML header check, etc.)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_transitions.py     # Unit tests for transition logic
│   │   ├── test_guards.py          # Unit tests for guard evaluations
│   │   ├── test_pipeline_runner.py # Integration tests for CLI
│   │   └── conftest.py             # Shared fixtures (sample pipeline-state.json)
│   ├── requirements.txt       # pydantic, pyyaml, pytest
│   └── README.md
└── README.md                  # Top-level tools overview

.vscode/
└── mcp.json                   # MCP server registration for VS Code
```

### 2.2 MCP Server — `tools/mcp-server/server.py`

**Framework:** FastMCP (Python SDK for Model Context Protocol)

**Tools exposed:**

#### Tool 1: `notify_orchestrator`

**Purpose:** Called by agents in auto mode after completing their stage. Triggers the pipeline-runner to compute the next transition and write the routing decision to `pipeline-state.json`.

```python
@mcp.tool()
async def notify_orchestrator(
    stage_completed: str,        # The stage that just completed (e.g., "implement")
    result_status: str,          # "complete" | "passed" | "failed" | "approved" | "revision-requested"
    artefact_path: str | None,   # Path to artefact produced (optional)
    result_payload: dict | None  # Structured result (e.g., tester_result block)
) -> dict:
    """
    Called by agents on stage completion in auto mode.
    
    1. Validates that the reported stage matches pipeline-state.json current_stage
    2. Writes the result to pipeline-state.json (stage status, artefact, result)
    3. Invokes pipeline-runner to compute the next transition
    4. Returns the routing decision for the orchestrator to present
    
    Returns:
        {
            "next_stage": "tester",
            "target_agent": "Tester",
            "handoff_prompt": "The pipeline is routing to you...",
            "gate_required": false,
            "pipeline_mode": "auto"
        }
    """
```

**Implementation notes:**
- The tool does NOT invoke the agent itself — it returns the routing decision
- In `supervised` mode, the tool returns the decision but the orchestrator waits for user click
- In `auto` mode, the orchestrator reads the returned decision and immediately invokes the next agent
- On error (guard failure, blocked state), returns `{"blocked": true, "reason": "..."}`

#### Tool 2: `validate_deferred_paths`

**Purpose:** Called by the orchestrator during Pipeline Close Protocol (§10) to verify that file paths in the code-reviewer's `deferred:` block actually exist.

```python
@mcp.tool()
async def validate_deferred_paths(
    deferred_items: list[dict]   # List of {id, title, file, detail, severity} dicts
) -> dict:
    """
    Validates each deferred item's file path exists and contains
    the symbol/pattern described in detail.
    
    Returns:
        {
            "validated": [...items with verified: true...],
            "unverified": [...items with verified: false, reason: "..."],
            "corrections": [...items where correct path was found...]
        }
    """
```

#### Tool 3: `get_pipeline_status`

**Purpose:** Returns the current pipeline state in a structured format for the orchestrator to present to the user. Avoids the orchestrator having to parse JSON itself.

```python
@mcp.tool()
async def get_pipeline_status() -> dict:
    """
    Reads pipeline-state.json and returns a formatted status summary.
    
    Returns:
        {
            "project": "...",
            "feature": "...",
            "current_stage": "...",
            "pipeline_mode": "supervised",
            "stages_summary": {...},
            "blocked_by": null,
            "next_transition": { ... computed by pipeline-runner ... }
        }
    """
```

### 2.3 Pipeline Runner — `tools/pipeline-runner/pipeline_runner.py`

**Type:** CLI state machine, invoked by the MCP server or directly from terminal.

**Interface:**

```
# Compute next transition (dry-run — does not write state)
python pipeline_runner.py next --state-file .github/pipeline-state.json

# Execute transition (writes the routing decision to state file)
python pipeline_runner.py advance --state-file .github/pipeline-state.json \
    --completed-stage implement --result-status complete

# Validate pre-flight (checks coverage_requirements, artefacts, gates)
python pipeline_runner.py preflight --state-file .github/pipeline-state.json \
    --target-stage tester

# Print current status
python pipeline_runner.py status --state-file .github/pipeline-state.json
```

**Core logic:**

```python
def compute_next_transition(state: PipelineState, event: CompletionEvent) -> TransitionResult:
    """
    Pure function. No side effects.
    
    1. Look up current_stage + event.result_status in the transition table
    2. Evaluate all guard conditions for matching transitions
    3. Return the first transition where all guards pass
    4. If no transition found, return BLOCKED with reason
    """
```

### 2.4 Transition Table — `tools/pipeline-runner/transitions.py`

**Data-driven design:** Transitions are defined as data, not if/else chains.

```python
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Transition:
    id: str                          # T-01, T-02, etc.
    from_stage: str                  # Stage key
    to_stage: str                    # Stage key
    event: str                       # "complete" | "passed" | "failed" | "approved" | "revision-requested"
    guards: list[str]                # Guard function names to evaluate
    gate: str | None                 # Supervision gate name (if required)
    hotfix_only: bool = False        # Only applies when type == "hotfix"
    priority: int = 0                # Higher priority evaluated first (for overlapping conditions)

TRANSITIONS: list[Transition] = [
    # --- Main Pipeline ---
    Transition("T-01", "intent",    "prd",       "complete",            ["artefact_exists"],                        "intent_approved"),
    Transition("T-02", "prd",       "architect",  "complete",           ["artefact_exists", "artefact_approved"],    None),
    Transition("T-03", "architect", "plan",       "complete",           ["artefact_exists", "artefact_approved"],    "adr_approved"),
    Transition("T-04", "plan",      "implement",  "complete",           ["artefact_exists", "artefact_approved"],    "plan_approved"),
    Transition("T-05", "implement", "tester",     "complete",           ["all_phases_done"],                         None),
    Transition("T-06", "tester",    "review",     "passed",             [],                                          None),
    Transition("T-07", "review",    "closed",     "approved",           ["no_security_deferrals_pending"],            "review_approved"),
    
    # --- Multi-Phase Loop ---
    Transition("T-13", "implement", "implement",  "phase_complete",     ["more_phases_remain"],                      None, priority=10),
    
    # --- Tester Retry ---
    Transition("T-14", "tester",    "implement",  "failed",             ["retry_budget_remaining"],                  None, priority=10),
    Transition("T-15", "tester",    "BLOCKED",    "failed",             ["retry_budget_exhausted"],                  None, priority=5),
    
    # --- Review Feedback ---
    Transition("T-16", "review",    "implement",  "revision-requested", [],                                          None, priority=10),
    
    # --- Hotfix ---
    Transition("T-18", "intake",    "implement",  "hotfix_known",       [],                                          None, hotfix_only=True),
    Transition("T-17", "intake",    "debug",      "hotfix_unknown",     [],                                          None, hotfix_only=True),
    Transition("T-19", "debug",     "implement",  "complete",           ["artefact_exists"],                         None, hotfix_only=True),
    Transition("T-20", "implement", "tester",     "complete",           [],                                          None, hotfix_only=True, priority=5),
    Transition("T-21", "tester",    "review",     "passed",             ["has_security_deferrals"],                  None, hotfix_only=True, priority=10),
    Transition("T-22", "tester",    "closed",     "passed",             ["no_security_deferrals"],                   None, hotfix_only=True, priority=5),
    
    # --- Deferred Re-Entry ---
    Transition("T-23", "closed",    "implement",  "deferred_reentry",   ["has_deferred_items"],                      None),
]
```

**Guard function registry** (in `guards.py`):

| Guard Name | Logic |
|------------|-------|
| `artefact_exists` | `os.path.exists(state.stages[from_stage].artefact)` |
| `artefact_approved` | Read artefact file, parse YAML header, check `approval: approved` |
| `all_phases_done` | `state.stages.implement.current_phase >= state.stages.implement.total_phases` |
| `more_phases_remain` | `current_phase < total_phases` |
| `retry_budget_remaining` | `state.stages.tester.retry_count < state.stages.tester.max_retries` |
| `retry_budget_exhausted` | `state.stages.tester.retry_count >= state.stages.tester.max_retries` |
| `has_security_deferrals` | Any item in `deferred[]` has `severity ∈ {security-nit, security}` |
| `no_security_deferrals` | No such items |
| `no_security_deferrals_pending` | No unresolved security deferrals from current cycle |
| `has_deferred_items` | `len(state.deferred) > 0` |
| `coverage_requirements_present` | `state._notes.handoff_payload.coverage_requirements` is non-empty (pre-flight only) |
| `no_blocking_escalations` | No files in `agent-docs/escalations/` with `severity: blocking` |

### 2.5 Schema — `tools/pipeline-runner/schema.py`

Pydantic models that mirror `pipeline-state.json`:

```python
from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime

StageStatus = Literal["not_started", "in_progress", "complete", "blocked"]
PipelineMode = Literal["supervised", "auto"]

class StageState(BaseModel):
    status: StageStatus = "not_started"
    artefact: str | None = None
    completed_at: datetime | None = None

class ImplementStageState(StageState):
    current_phase: int = 0
    total_phases: int = 1
    retry_count: int = 0
    max_retries: int = 3

class TesterStageState(StageState):
    retry_count: int = 0
    max_retries: int = 3

class SupervisionGates(BaseModel):
    intent_approved: bool = False
    adr_approved: bool = False
    plan_approved: bool = False
    review_approved: bool = False

class DeferredItem(BaseModel):
    id: str
    title: str
    file: str
    detail: str
    severity: str

class HandoffPayload(BaseModel):
    target_agent: str | None = None
    scope: str | None = None
    summary: str | None = None
    required_tests: list[str] = Field(default_factory=list)
    exit_criteria: str | None = None
    upstream_artefact: str | None = None
    coverage_requirements: list[str] = Field(default_factory=list)

class Notes(BaseModel):
    handoff_payload: HandoffPayload | None = None
    # ... hotfix_brief etc.

class PipelineState(BaseModel):
    project: str
    feature: str
    pipeline_version: str = "1.0"
    pipeline_mode: PipelineMode = "supervised"
    type: str | None = None  # "hotfix" or None
    current_stage: str
    stages: dict[str, StageState | ImplementStageState | TesterStageState]
    supervision_gates: SupervisionGates = Field(default_factory=SupervisionGates)
    deferred: list[DeferredItem] = Field(default_factory=list)
    blocked_by: str | None = None
    last_updated: datetime | None = None
    _notes: Notes | None = None

class CompletionEvent(BaseModel):
    stage_completed: str
    result_status: str  # "complete" | "passed" | "failed" | "approved" | "revision-requested"
    artefact_path: str | None = None
    result_payload: dict | None = None

class TransitionResult(BaseModel):
    transition_id: str | None = None
    next_stage: str | None = None
    target_agent: str | None = None
    gate_required: str | None = None
    gate_satisfied: bool = True
    blocked: bool = False
    blocked_reason: str | None = None
    pipeline_mode: PipelineMode = "supervised"
```

### 2.6 `.vscode/mcp.json`

```json
{
  "servers": {
    "pipeline-mcp": {
      "type": "stdio",
      "command": "python",
      "args": ["tools/mcp-server/server.py"],
      "env": {
        "PIPELINE_STATE_PATH": ".github/pipeline-state.json"
      }
    }
  }
}
```

### 2.7 Test Design — `tools/pipeline-runner/tests/test_transitions.py`

**Coverage targets:**

| Test Category | Tests | Description |
|---------------|-------|-------------|
| Happy path (T-01 → T-07) | 7 tests | Each main pipeline transition fires correctly |
| Multi-phase loop (T-13) | 2 tests | Phase increment, final phase → tester |
| Tester retry (T-14, T-15) | 3 tests | Retry within budget, retry exhausted → BLOCKED, retry count incremented |
| Review loop (T-16) | 2 tests | revision-requested → implement, approved → closed |
| Hotfix path (T-17 → T-22) | 6 tests | Both hotfix entry points, security gate branch |
| Deferred re-entry (T-23) | 2 tests | Re-entry with items, no-op when empty |
| Guard failures | 5 tests | Missing artefact, missing approval, gate not satisfied, escalation blocking |
| pipeline_mode branching | 3 tests | auto returns gate_satisfied=true without user, supervised requires gate |
| Blocked → recovery (T-27) | 2 tests | Unblock after fix, re-evaluate transition |
| Edge cases | 3 tests | Unknown stage, invalid event, duplicate completion |

**Total: ~35 unit tests.**

**Testing strategy:**
- All tests use in-memory `PipelineState` objects — no file I/O
- `conftest.py` provides factory fixtures: `make_state(current_stage, **overrides)`
- Guard functions are tested independently in `test_guards.py`
- MCP server tested separately (integration test with mock file system)

---

## Task 3 — Orchestrator Agent Changes

### 3.1 Overview of Changes

The orchestrator must shift from **computing** routing decisions to **reading** them. The LLM retains responsibility for:
- Intake classification (§9)
- `handoff_payload` construction (extracting `coverage_requirements[]` from artefacts)
- Human-facing summaries of pipeline status
- Presenting handoff buttons in supervised mode

The orchestrator **relinquishes** to pipeline-runner:
- All transition logic (which stage comes next)
- Guard evaluation (artefact exists, approval checked, gates satisfied)
- Blocked state management

### 3.2 Changes to Orchestrator §1 (Read Pipeline State First)

**Current:** Orchestrator reads `pipeline-state.json` to understand position.
**Change:** After reading, orchestrator also reads `_notes._routing_decision` (a new field written by pipeline-runner):

```json
{
  "_notes": {
    "_routing_decision": {
      "transition_id": "T-05",
      "next_stage": "tester",
      "target_agent": "Tester",
      "gate_required": null,
      "gate_satisfied": true,
      "blocked": false,
      "pipeline_mode": "supervised"
    }
  }
}
```

**New §1 logic:**
1. Read `pipeline-state.json`
2. If `_notes._routing_decision` exists and `blocked == false`:
   - Read `pipeline_mode`
   - If `supervised`: present the routing decision as a handoff button, WAIT for user click
   - If `auto`: immediately invoke the target agent with the handoff prompt
3. If `_notes._routing_decision.blocked == true`:
   - Report the `blocked_reason` to the user
   - STOP
4. If `_notes._routing_decision` does not exist:
   - This is a fresh session or intake — proceed with intake classification (§9)

### 3.3 Changes to Orchestrator §3 (Routing Logic)

**Current:** §3 contains the full routing sequence as LLM instructions. The LLM evaluates which agent comes next.

**Change:** Replace the routing sequence with a delegation pattern:

```markdown
### 3. Routing Logic

**The pipeline-runner owns all routing decisions.** Do NOT infer the next stage yourself.

After any agent completes a stage:
1. The agent calls `notify_orchestrator` MCP tool (auto mode) or clicks
   `Return to Orchestrator` (supervised mode)
2. Pipeline-runner computes the transition and writes `_notes._routing_decision`
   to pipeline-state.json
3. You READ this decision and act on it:
   - Present the handoff button for the target agent (supervised)
   - Invoke the target agent (auto)

You still evaluate:
- Intake classification (§9 — what kind of request is this?)
- handoff_payload construction (§3 GAP-I1 — what does the receiving agent need?)
- Pipeline Close Protocol (§10 — deferred item handling)

You do NOT evaluate:
- Which stage comes next (read from _routing_decision)
- Whether guards are satisfied (pipeline-runner checked this)
- Whether gates are approved (pipeline-runner checked this)
```

### 3.4 Changes for `pipeline_mode` Branching

**New §3.1:**

```markdown
### 3.1 Pipeline Mode

Read `pipeline_mode` from pipeline-state.json root (default: `"supervised"`).

| Mode | Behaviour |
|------|-----------|
| `supervised` | Present routing as handoff button with `send: false`. WAIT for user click. The human remains in the loop at every transition. |
| `auto` | Read `_notes._routing_decision`, construct the handoff prompt, and immediately invoke the target agent. Only STOP at supervision gates where `gate_satisfied == false`. |

**Switching modes:** The user can set `pipeline_mode` in pipeline-state.json at any time.
The mode is checked at each transition, not once at pipeline start.
```

### 3.5 Supervised Mode Preservation (Critical)

**No breaking changes to supervised mode:**

In supervised mode, the flow is:
1. Agent completes → user clicks `Return to Orchestrator`
2. User opens NEW chat session with `@Orchestrator`
3. Orchestrator reads `pipeline-state.json`
4. Orchestrator calls `get_pipeline_status` MCP tool (which internally calls pipeline-runner to compute next transition)
5. Orchestrator presents the handoff button
6. User clicks button → next agent runs in same session

**Key invariant:** The user always clicks the handoff button. Pipeline-runner writes the routing decision, but the orchestrator still presents it as a clickable button. No change to the user experience.

### 3.6 Summary of §-Level Changes

| Section | Change Type | Description |
|---------|-------------|-------------|
| §1 | Modified | Read `_notes._routing_decision` after reading state; branch on `pipeline_mode` |
| §2 | Unchanged | Artefact validation delegated to pipeline-runner guards, but orchestrator still reports failures |
| §3 | Major rewrite | Remove transition inference; delegate to pipeline-runner; keep intake + payload construction |
| §3.1 | New | Pipeline mode branching documentation |
| §4 | Modified | Gates still listed, but checking delegated to pipeline-runner; orchestrator only presents the gate prompt |
| §5 | Unchanged | State updates still performed by orchestrator (or MCP tool in auto) |
| §9 | Unchanged | Intake classification stays as LLM responsibility |
| §10 | Modified | Pipeline Close uses `validate_deferred_paths` MCP tool |
| §11 | Modified | Tester retry loop decisions come from pipeline-runner (T-14/T-15); orchestrator just reads |
| §12 | Modified | Hotfix routing comes from pipeline-runner (T-17-T-22); orchestrator just reads |

---

## Task 4 — Updated Implementation Order

### 4.1 GAP-I1 Completion Status

| Component | Status | Location |
|-----------|--------|----------|
| Fidelity Check — Planner agent | ✅ Done | `planner.agent.md` line 54 |
| Fidelity Check — implement agent | ✅ Done | `implement.agent.md` line 53 |
| Fidelity Check — tester agent | ✅ Done | `tester.agent.md` line 31 |
| Fidelity Check — code-reviewer agent | ✅ Done | `code-reviewer.agent.md` line 41 |
| `coverage_requirements[]` schema | ✅ Done | `pipeline-state/SKILL.md` line 167 |
| Orchestrator writes `coverage_requirements[]` | ✅ Done | `orchestrator.agent.md` §3 line 128 |
| Pipeline-runner pre-flight check | ❌ Not started | — |

### 4.2 Revised Phase Plan

#### Phase 1: MCP Server + Schema (Foundation)

**Scope:**
- `tools/mcp-server/server.py` — FastMCP server with 3 tools
- `tools/pipeline-runner/schema.py` — Pydantic models
- `.vscode/mcp.json` — server registration
- `tools/mcp-server/requirements.txt`

**Exit criteria:**
- MCP server starts and all 3 tools respond to schema introspection
- Pydantic models serialize/deserialize `pipeline-state.template.json` without error

**Dependencies:** None — this is the foundation.

#### Phase 2: Pipeline Runner + Transition Table + Unit Tests

**Scope:**
- `tools/pipeline-runner/transitions.py` — full transition table (T-01 through T-27)
- `tools/pipeline-runner/guards.py` — all guard implementations
- `tools/pipeline-runner/pipeline_runner.py` — CLI with `next`, `advance`, `preflight`, `status` subcommands
- `tools/pipeline-runner/tests/` — full test suite (~35 tests)
- `tools/pipeline-runner/requirements.txt`

**Exit criteria:**
- `python pipeline_runner.py status` reads state and reports correctly
- `python pipeline_runner.py next` computes the correct transition for every state
- `python pipeline_runner.py advance` writes the correct `_routing_decision` to state file
- All 35 tests pass
- `python pipeline_runner.py preflight --target-stage tester` checks `coverage_requirements[]`

**Dependencies:** Phase 1 (schema).

#### Phase 3: Pre-Flight Check for `coverage_requirements[]` (GAP-I1 Completion)

**Scope:**
- `pipeline_runner.py preflight` subcommand validates:
  - `coverage_requirements[]` is non-empty when `upstream_artefact` exists
  - Each item in `coverage_requirements[]` is a non-empty string
  - Logs warning if `upstream_artefact` path doesn't exist on disk
- MCP server wires `notify_orchestrator` to call `preflight` before `advance`

**Exit criteria:**
- Pre-flight rejects a transition where `coverage_requirements` is empty but upstream artefact exists
- Pre-flight passes when `coverage_requirements` is properly populated
- Test coverage for both cases

**Dependencies:** Phase 2 (runner + guards).

**Note:** This is the ONLY remaining GAP-I1 work. The agent-level fidelity checks are already in place.

#### Phase 4: Auto Mode Wire-Up (Agent Completion Protocols)

**Scope:**
- Add Completion Reporting Protocol §8 to 6 agents:
  - PRD (`prd.agent.md`)
  - Architect (`architect.agent.md`)
  - Debug (`debug.agent.md`)
  - Security Analyst (`security-analyst.agent.md`)
  - UX Designer (`ux-designer.agent.md`)
  - UI/UX Designer (`ui-ux-designer.agent.md`)
- Add `Return to Orchestrator` handoff (with `send: false`) to all 6
- Add `HARD STOP` instruction to all 6
- Update orchestrator §1, §3, §3.1 per Task 3 design
- Add `"pipeline_mode": "supervised"` to `pipeline-state.template.json`
- Wire all 9+ agent completion protocols to mention `notify_orchestrator` MCP tool for auto mode:
  ```
  If pipeline_mode == "auto": call notify_orchestrator tool instead of
  presenting Return to Orchestrator button.
  ```

**Exit criteria:**
- All main-pipeline agents have identical completion protocol structure
- `pipeline-state.template.json` includes `pipeline_mode` field
- Orchestrator reads `_routing_decision` instead of inferring transitions
- Supervised mode works identically to today (no regressions)
- Auto mode completes a full `intent → closed` pipeline with mock artefacts

**Dependencies:** Phase 3.

### 4.3 Ordering Rationale

```
Phase 1 (MCP Server)
    │
    ▼
Phase 2 (Pipeline Runner + Tests)     ← This is the critical path
    │
    ▼
Phase 3 (Pre-flight / GAP-I1)         ← Smallest scope, completes GAP-I1
    │
    ▼
Phase 4 (Auto Mode Wire-Up)           ← Touches many files, highest change risk
```

Phase 1 and 2 can be developed by the same agent in one session each. Phase 3 is a small addition (~30 lines of logic + tests). Phase 4 is the riskiest because it modifies 8+ agent files and the orchestrator — it should be a dedicated session with full regression testing.

---

## Risks & Open Questions

### Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Phase |
|----|------|-----------|--------|------------|-------|
| R-01 | MCP server is not invoked by VS Code (misconfigured mcp.json) | Medium | High | Manual testing: verify tool appears in Copilot tool list before Phase 2 | 1 |
| R-02 | Pipeline-runner path resolution fails (relative vs absolute paths) | Medium | Medium | All paths resolved relative to workspace root via `pathlib`; test with both absolute and relative | 2 |
| R-03 | YAML header parsing is fragile (different frontmatter formats) | Medium | High | Use `python-frontmatter` library; add tests for edge cases (no header, partial header, TOML header) | 2 |
| R-04 | Transition table has a gap for an edge case not covered | Low | High | The 35-test suite covers every transition; add a "no matching transition" catch-all that BLOCKs with diagnostic info | 2 |
| R-05 | Phase 4 agent file edits introduce regressions in supervised mode | Medium | Critical | Phase 4 must include a supervised-mode smoke test: manual walkthrough of intent→closed with button clicks | 4 |
| R-06 | `notify_orchestrator` is called but orchestrator is not in the chat session | Medium | Medium | MCP tool writes to file; orchestrator reads on next invocation — async by design | 1 |
| R-07 | Parallel stage support deferred — plan-defined parallel paths will fail | Low | Medium | Phase 2 transition table returns BLOCKED with "parallel stages not yet supported" message | 2 |

### Open Questions

| ID | Question | Impact | Proposed Answer |
|----|----------|--------|----------------|
| Q-01 | Should `pipeline-runner` be a Python script or a Node.js script? | Architecture | Python — matches the agent pool's primary language, uses Pydantic for schema validation which is already a project dependency pattern |
| Q-02 | Should `notify_orchestrator` be async (fire-and-forget) or synchronous? | Auto mode UX | Synchronous — the MCP tool computes the transition and returns the result in the same call. The orchestrator needs the result immediately to construct the handoff. |
| Q-03 | How does the orchestrator know to call `get_pipeline_status` on a fresh session? | Startup flow | §1 already says "Read pipeline-state.json first". Replace with "Call `get_pipeline_status` MCP tool first" — this computes `_routing_decision` as a side effect. |
| Q-04 | Should `transitions.py` be a Python file or YAML/JSON data? | Maintainability | Python dataclass — type-safe, guard functions are Python callables, IDE support for refactoring. A YAML version could be added later for non-developer editing. |
| Q-05 | What happens when the user manually edits `pipeline-state.json` mid-pipeline? | Data integrity | Pipeline-runner re-evaluates from current state on every invocation. Manual edits are a supported workflow (e.g., resetting retry_count). The runner is stateless — it computes from whatever is in the file. |

---

## Appendix A: Agent ↔ Stage Mapping (Complete)

| Agent File | Stage Key(s) | Has Return Handoff | Has HARD STOP | Has Completion §8 | Needs Phase 4 Update |
|------------|-------------|-------------------|---------------|-------------------|---------------------|
| `implement.agent.md` | `implement` | ✅ | ✅ | ✅ | Wire `notify_orchestrator` |
| `tester.agent.md` | `tester` | ✅ | ✅ | ✅ | Wire `notify_orchestrator` |
| `code-reviewer.agent.md` | `review` | ✅ | ✅ | ✅ | Wire `notify_orchestrator` |
| `planner.agent.md` | `plan` | ❌ (has Start Implementation) | ❌ | ❌ | Add Return + HARD STOP + §8 + wire |
| `prd.agent.md` | `prd` | ❌ | ❌ | ❌ | Add Return + HARD STOP + §8 + wire |
| `architect.agent.md` | `architect` | ❌ | ❌ | ❌ | Add Return + HARD STOP + §8 + wire |
| `debug.agent.md` | `debug` | ❌ | ❌ | ❌ | Add Return + HARD STOP + §8 + wire |
| `security-analyst.agent.md` | `security` | ❌ | ❌ | ❌ | Add Return + HARD STOP + §8 + wire |
| `ux-designer.agent.md` | `ux_research` | ❌ | ❌ | ❌ | Add Return + HARD STOP + §8 + wire |
| `ui-ux-designer.agent.md` | `ui_design` | ❌ | ❌ | ❌ | Add Return + HARD STOP + §8 + wire |
| `streamlit-developer.agent.md` | `implement` | ✅ | ✅ | ✅ | Wire `notify_orchestrator` |
| `frontend-developer.agent.md` | `implement` | ✅ | ✅ | ✅ | Wire `notify_orchestrator` |
| `data-engineer.agent.md` | `implement` | ✅ | ✅ | ✅ | Wire `notify_orchestrator` |
| `sql-expert.agent.md` | `implement` | ✅ | ✅ | ✅ | Wire `notify_orchestrator` |
| `devops.agent.md` | `devops` | ✅ | ✅ | ✅ | Wire `notify_orchestrator` |
| `janitor.agent.md` | `janitor` | ✅ | ✅ | ✅ | Wire `notify_orchestrator` |

**Total agents needing Phase 4 changes:** 16 (7 new Return+HARD STOP+§8, 9 wire `notify_orchestrator` into existing §8)

*Note: `planner.agent.md` has a `Start Implementation` handoff that routes directly to implement — this must be replaced with `Return to Orchestrator` in Phase 4 to ensure pipeline-runner controls the transition.*

---

## Appendix B: Schema Additions to `pipeline-state.json`

Fields to add to `pipeline-state.template.json`:

```json
{
  "pipeline_mode": "supervised",
  "_notes": {
    "handoff_payload": null,
    "_routing_decision": null,
    "_hotfix_brief": null
  }
}
```

`_routing_decision` structure (written by pipeline-runner, read by orchestrator):

```json
{
  "_routing_decision": {
    "transition_id": "T-05",
    "next_stage": "tester",
    "target_agent": "Tester",
    "handoff_prompt": "The pipeline is routing to you. Read pipeline-state.json first...",
    "gate_required": null,
    "gate_satisfied": true,
    "blocked": false,
    "blocked_reason": null,
    "computed_at": "2025-02-21T10:30:00Z"
  }
}
```
