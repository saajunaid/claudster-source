# JUNAI Pipeline Commands

This is the operator reference for `.github/tools/pipeline-runner/pipeline_runner.py`, exposed through:

```powershell
junai pipeline <command> [options]
```

From the repo root, the direct runner form is also valid:

```powershell
python .github/tools/pipeline-runner/pipeline_runner.py <command> [options]
```

## Common Flows

### Start a New Pipeline

```powershell
junai pipeline init --project <project-name> --feature <feature-slug>
```

Overwrite an existing state file:

```powershell
junai pipeline init --project <project-name> --feature <feature-slug> --force
```

Start a hotfix pipeline:

```powershell
junai pipeline init --project <project-name> --feature <feature-slug> --type hotfix
```

### Run From an Existing Approved Plan

Recommended safe path:

```powershell
junai pipeline fast-track --from-plan .github/plans/<plan>.md --entry preflight --mode supervised
```

Unattended autopilot path:

```powershell
junai pipeline fast-track --from-plan .github/plans/<plan>.md --entry preflight --mode autopilot
```

Only enter implementation directly when the same plan already has a PASS preflight report:

```powershell
junai pipeline fast-track --from-plan .github/plans/<plan>.md --entry implement --mode autopilot
```

If `.github/pipeline-state.json` does not exist yet, initialize during fast-track:

```powershell
junai pipeline fast-track --from-plan .github/plans/<plan>.md --entry preflight --mode autopilot --project <project-name> --feature <feature-slug>
```

Full plan-run path with readiness scoring:

```powershell
junai pipeline run-plan --from-plan .github/plans/<plan>.md --entry preflight --mode autopilot
junai pipeline resume
junai pipeline last-handoff
```

`run-plan` scores the plan, fast-tracks state only when the plan is usable, and returns the next command. In a single-agent host, the same active agent should execute the role described by `last-handoff`.

### Discover Existing Artefacts

Use the current state feature:

```powershell
junai pipeline discover-artefacts
```

Specify a feature slug:

```powershell
junai pipeline discover-artefacts --feature <feature-slug>
```

Write machine-readable discovery output to `.github/agent-docs/artifacts.json`:

```powershell
junai pipeline discover-artefacts --feature <feature-slug> --write-registry
```

### Diagnose Pipeline Health

```powershell
junai pipeline doctor
```

This checks for state problems, missing artefacts, unapproved completed-stage artefacts, stale routing symptoms, blocked state, and legacy `agent-docs/` usage.

### Inspect Current Routing Context

```powershell
junai pipeline status
junai pipeline resume
junai pipeline history
junai pipeline last-handoff
junai pipeline dashboard
```

Use `status` for the current stage and progress line. Use `resume` for the safest next action. Use `history` to see routing/stage logs. Use `last-handoff` to inspect the latest `_routing_decision` and `handoff_payload`. Use `dashboard` for a markdown report in `.github/agent-docs/pipeline-dashboard.md`.

## Command Reference

### `init`

Creates `.github/pipeline-state.json` from `.github/pipeline-state.template.json`.

```powershell
junai pipeline init --project <project-name> --feature <feature-slug> [--type feature|hotfix] [--force]
```

Options:

| Option | Required | Purpose |
|---|---:|---|
| `--project` | Yes | Project display/name key written to state |
| `--feature` | Yes | Feature slug used for artefact discovery and routing |
| `--type` | No | Optional pipeline type, commonly `hotfix` |
| `--force` | No | Overwrite an existing state file |

### `status`

Prints current state as JSON.

```powershell
junai pipeline status
```

Includes `project`, `feature`, `current_stage`, `pipeline_mode`, `blocked_by`, stage records, and `progress_line`.

### `mode`

Sets execution mode.

```powershell
junai pipeline mode --value supervised
junai pipeline mode --value assisted
junai pipeline mode --value autopilot
```

Modes:

| Mode | Meaning |
|---|---|
| `supervised` | Human confirms handoffs/gates |
| `assisted` | Agent handoffs can proceed automatically, but gates still ask |
| `autopilot` | Routine gates auto-satisfied except intent approval in normal intake; halts on blockers |

### `gate`

Marks a supervision gate as satisfied.

```powershell
junai pipeline gate --name intent_approved
junai pipeline gate --name adr_approved
junai pipeline gate --name plan_approved
junai pipeline gate --name plan_validated
junai pipeline gate --name review_approved
```

### `discover-artefacts`

Finds existing PRD, architecture, plan, and preflight artefacts for a feature.

```powershell
junai pipeline discover-artefacts [--feature <feature-slug>] [--write-registry]
```

Searches canonical paths first:

| Artefact | Canonical path |
|---|---|
| Plans | `.github/plans/*.md` |
| PRDs | `.github/agent-docs/prd/*.md` |
| Architecture | `.github/agent-docs/architecture/*.md`, `docs/architecture/**` |
| Preflight | `.github/agent-docs/preflight-report.md` |

Legacy `agent-docs/` paths are retained as fallback.

### `fast-track`

Aligns state from an approved plan.

```powershell
junai pipeline fast-track --from-plan <path> [--entry preflight|implement] [--mode supervised|assisted|autopilot] [--project <name>] [--feature <slug>]
```

Behavior:

| Entry | Behavior |
|---|---|
| `preflight` | Marks upstream stages complete using the approved plan as source artefact, satisfies upstream gates, routes to Preflight |
| `implement` | Requires PASS preflight for the exact plan, satisfies `plan_validated`, routes to Implement |

### `run-plan`

Scores an approved plan, aligns state, and routes to the requested entry stage.

```powershell
junai pipeline run-plan --from-plan <path> [--entry preflight|implement] [--mode supervised|assisted|autopilot] [--project <name>] [--feature <slug>]
```

Use this when you want the pipeline to run from the plan as the source of truth. It combines `plan-score` and `fast-track`; direct `implement` entry still requires a PASS preflight report for the same plan.

### `parse-plan`

Parses numbered `## Phase N` sections and extracts phase metadata.

```powershell
junai pipeline parse-plan --plan <path>
```

Returns phase number, heading, assigned agent when present, referenced skills/instructions/files, and static size metrics.

### `plan-score`

Scores plan readiness for automated or low-intervention execution.

```powershell
junai pipeline plan-score --plan <path>
```

Checks approval, numbered phases, agent assignments, validation detail, traceability, scope-change declaration, and static context risk.

### `context-guard`

Estimates whether a plan phase is small enough for one focused execution session.

```powershell
junai pipeline context-guard --plan <path> [--phase <n>]
```

This is a conservative static estimate based on phase size and risk words. It does not inspect the live model context window.

### `model-route`

Recommends a deterministic model for a stage or plan phase.

```powershell
junai pipeline model-route --stage <stage> [--plan <path>] [--phase <n>]
```

In hosts that cannot switch models or agents automatically, treat this as routing guidance for the active session.

### `preflight`

Runs runner-level preflight checks for a target stage.

```powershell
junai pipeline preflight --target-stage tester
```

This is not the full Preflight agent validation; it is a deterministic runner check for required state inputs.

### `next`

Computes the next transition without writing state.

```powershell
junai pipeline next
junai pipeline next --completed-stage <stage> --result-status <status>
junai pipeline next --completed-stage <stage> --result-status <status> --artefact-path <path>
```

Common result statuses:

| Stage | Common status |
|---|---|
| `intent` | `complete` |
| `prd` | `complete` |
| `architect` | `complete` |
| `plan` | `complete` |
| `preflight` | `passed` or `failed` |
| `implement` | `phase_complete` or `complete` |
| `tester` | `passed` or `failed` |
| `review` | `approved` or `revision-requested` |

### `advance`

Computes and persists a transition.

```powershell
junai pipeline advance --completed-stage <stage> --result-status <status> [--artefact-path <path>] [--result-payload '<json>']
```

Examples:

```powershell
junai pipeline advance --completed-stage plan --result-status complete --artefact-path .github/plans/<plan>.md
junai pipeline advance --completed-stage preflight --result-status passed --artefact-path .github/agent-docs/preflight-report.md
junai pipeline advance --completed-stage tester --result-status passed
junai pipeline advance --completed-stage review --result-status approved --artefact-path .github/agent-docs/reviews/review-<feature>.md
```

Duplicate completion is idempotent: if the completed stage is already `complete`, the command returns a clean no-op and does not advance again.

### `skip`

Skips the current skippable stage.

```powershell
junai pipeline skip --stage <stage> --reason "<why>"
```

Unskippable stages:

```text
implement, anchor, tester, closed, BLOCKED
```

### `doctor`

Diagnoses state and artefact health.

```powershell
junai pipeline doctor
```

Use before resuming a stuck pipeline or after manual edits.

### `resume`

Prints the safest next action for paused work.

```powershell
junai pipeline resume
```

It runs the same health checks as `doctor`, then recommends `doctor`, `last-handoff`, or `next` depending on the state.

### `dashboard`

Writes a markdown dashboard report.

```powershell
junai pipeline dashboard
junai pipeline dashboard --output .github/agent-docs/pipeline-dashboard.md
```

The report includes stage, mode, progress, gate state, doctor results, latest routing decision, and known artefacts.

### `halt-info`

Classifies a halt/blocker and returns recovery commands.

```powershell
junai pipeline halt-info --reason "preflight failed on plan"
junai pipeline halt-info
```

Without `--reason`, it uses `blocked_by` from state when present.

### `evidence`

Writes an execution evidence bundle and records it in `_notes._evidence_bundles`.

```powershell
junai pipeline evidence --stage implement --phase 1 --status passed --file <path> --test "<test>" --command "<command>" --risk "<risk>"
```

Evidence bundles are written to `.github/agent-docs/evidence/`.

### `history`

Prints `_routing_history`, `_stage_log`, and `_stage_history`.

```powershell
junai pipeline history
```

### `last-handoff`

Prints the current `_routing_decision` and `handoff_payload`.

```powershell
junai pipeline last-handoff
```

### `transitions`

Prints registry transitions as JSON.

```powershell
junai pipeline transitions
```

## State File Override

Most commands accept:

```powershell
--state-file <path>
```

Example:

```powershell
junai pipeline status --state-file E:\Projects\my-app\.github\pipeline-state.json
```

## Autopilot Notes

Autopilot is a state/routing mode, not a guarantee that your editor can switch chat personas automatically.

In environments with agent handoff support, Orchestrator can route to the target agent automatically. In a single-agent environment such as a Codex session in VS Code, the runner can still:

- maintain the state machine
- discover artefacts
- fast-track from a plan
- compute next transitions
- record handoff payloads
- diagnose health

But the same active agent may need to execute the target role manually by reading `last-handoff`, loading the relevant instructions, and doing the work for the current stage.

Recommended single-agent loop:

```powershell
junai pipeline fast-track --from-plan .github/plans/<plan>.md --entry preflight --mode autopilot
junai pipeline last-handoff
# Act as the target stage/agent described by last-handoff.
junai pipeline advance --completed-stage preflight --result-status passed --artefact-path .github/agent-docs/preflight-report.md
junai pipeline last-handoff
# Act as Implement for the next phase.
```

In short: autopilot can automate routing and gates; it cannot create missing editor-level agent switching where the host does not provide it.
