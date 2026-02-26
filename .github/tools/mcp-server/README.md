# Pipeline MCP Server

This server provides deterministic-routing support tools for the orchestrator.

## Tools

- `notify_orchestrator(stage_completed, result_status, artefact_path?, result_payload?)`
  - Persists completion result into `.github/pipeline-state.json`
  - Invokes `tools/pipeline-runner/pipeline_runner.py advance`
  - Writes routing decision into `_notes._routing_decision`
- `validate_deferred_paths(deferred_items)`
  - Validates deferred item file paths
  - Attempts filename-based path correction
- `get_pipeline_status()`
  - Returns current state summary, latest `_routing_decision`, and formatted `progress_line`
- `skip_stage(stage_to_skip, reason)`
  - Skips the current stage with auto-gate satisfaction
  - Blocked on unskippable stages: `implement`, `anchor`, `tester`, `closed`, `BLOCKED`
- `pipeline_init(project_name, feature_slug, pipeline_type?, force?)`
  - Initialises a new pipeline with active-pipeline guard
- `pipeline_reset(confirm)`
  - Force-clears and restarts the pipeline
- `set_pipeline_mode(mode)`
  - Switches between `supervised`, `assisted`, `autopilot`
- `satisfy_gate(gate_name)`
  - Manually satisfies a named supervision gate
- `run_command(command)`
  - Executes a shell command from chat context

## Configuration

The server reads `PIPELINE_STATE_PATH` from environment.

- Default: `.github/pipeline-state.json` (relative to workspace root)

## Run (manual)

```powershell
python tools/mcp-server/server.py
```

## Install dependencies

```powershell
.venv\Scripts\python -m pip install -r tools/mcp-server/requirements.txt
```

## Phase 1 Validation Checklist

1. Server starts without import/runtime errors
2. MCP client can introspect 3 tools
3. `tools/pipeline-runner/schema.py` can load and dump `.github/pipeline-state.template.json`
