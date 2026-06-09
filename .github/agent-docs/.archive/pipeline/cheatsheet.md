# JUNAI Pipeline Cheatsheet

> Single-page reference for the `junai` CLI, 9 pipeline stages, mode/gate guide,
> and recovery procedures.  Keep this tab open while running the pipeline.

---

## Zero-Friction Setup (VS Code Extension)

Install the **junai — Agent Pipeline** extension from the VS Code Marketplace:
```
code --install-extension junai-labs.junai
```
Or search `junai` in the Extensions panel. Then run **`junai: Initialize Agent Pipeline`** from the command palette to deploy the pool into any open workspace.

> Manual setup alternative: `junai-pull` (requires junai repo cloned — see README Path B).

---

## Quick Commands

```
junai pipeline status                           # current stage, mode, last_updated
junai pipeline init   --project "X" --feature "Y" [--type feature|hotfix]
junai pipeline mode   --value supervised|assisted|autopilot
junai pipeline gate   --name <gate_name>        # satisfy a supervision gate
junai pipeline next   [--event <event>]         # dry-run: what would advance do?
junai pipeline advance --event <event>          # actually advance
junai pipeline transitions                      # list all T-xx transitions
junai pipeline preflight --target-stage <stage> # pre-flight checks

junai agent list                                # compliance table: all agents
junai agent make      --name <xyz> [--role executing|advisory]
junai agent validate  --name <xyz>
junai agent diff      --name <xyz>              # dry-run preview of onboard
junai agent onboard   --name <xyz> [--yes]
junai agent inspect   --name <xyz>
junai agent remove    --name <xyz> [--force]
```

---

## 9 Pipeline Stages

| # | Stage        | Agent(s)             | Key artefact                        | Advance event            |
|---|--------------|----------------------|-------------------------------------|--------------------------|
| 1 | `intent`     | Orchestrator         | INTENT.md                           | `intent_complete`        |
| 2 | `prd`        | PRD                  | PRD.md                              | `prd_complete`           |
| 3 | `architect`  | Architect            | HLD/LLD docs                        | `architect_complete`     |
| 4 | `plan`       | Plan                 | PLAN.md / tasks                     | `plan_complete`          |
| 5 | `implement`  | Implement            | committed code                      | `implement_complete`     |
| 6 | `tester`     | Tester               | test file, coverage doc             | `tester_complete`        |
| 7 | `review`     | Code Reviewer        | review report                       | `review_complete`        |
| 8 | `deploy`     | DevOps               | deployment artefact                 | `deploy_complete`        |
| 9 | `closed`     | Orchestrator         | —                                   | `pipeline_closed`        |

Hotfix fast-track: `intent → implement → tester → closed` (plan/architect/review optional).

---

## Optional Enrichment Stage

| Stage                | Agent               | Key artefact              | Trigger event       |
|----------------------|---------------------|---------------------------|---------------------|
| `knowledge_transfer` | Knowledge Transfer  | `docs/gold-nuggets-log.md`| `knowledge_capture` |

**Not part of the main pipeline flow.** Human-triggered only — the user decides when a session is worth capturing. Invoke after any of:

- `anchor` — adversarial passes produce high-signal nuggets; also captures explicitly rejected approaches
- `implement` — after working code ships
- `debug` — after an incident is resolved (root cause + fix becomes the primary nugget)

**Terminal stage**: no downstream dependents. Does not block or advance `current_stage`. Invoke directly:

```
@knowledge-transfer
```

Or via Orchestrator after a stage completes:

```
# After Anchor/Implement/Debug completes — user says:
"Capture knowledge from this session"
# Orchestrator fires: junai pipeline advance --event knowledge_capture
```

> **Rule**: Do NOT invoke after `@architect` alone — architecture is intent, not demonstrated truth. Capture after code exists.

---

## Pipeline Mode Guide

| Mode          | What happens at each stage transition                                              |
|---------------|------------------------------------------------------------------------------------|
| `supervised`  | Shows **handoff button** and **WAITS** for user click                              |
| `assisted`    | Orchestrator invokes next agent **immediately**; gates still require your approval |
| `autopilot`   | Invokes immediately; all gates auto-satisfied except `intent_approved` ⚠️ *beta*      |

Switch mode:
```
junai pipeline mode --value assisted    # auto-routing, gates still require your approval
junai pipeline mode --value autopilot   # auto-routing, gates auto-satisfied (beta)
junai pipeline mode --value supervised  # return to fully gated routing
```

> **Rule:** Start all new pipelines in `supervised`. Switch to `assisted` after a clean supervised run. Use `autopilot` only after verifying behaviour in `assisted` first.

---

## Supervision Gates

Gates are named checkpoints that **block** the pipeline until explicitly satisfied.

```
junai pipeline gate --name pre_deploy            # satisfy a gate
junai pipeline status                            # check blocked_by field
```

Common gates and who satisfies them:

| Gate name           | When raised                              | Who satisfies it             |
|---------------------|------------------------------------------|------------------------------|
| `pre_deploy`        | Review completes in prod pipeline        | Human / DevOps sign-off      |
| `tester_retry_limit`| Implement retried ≥ 3× without passing  | Human diagnosis required     |
| `security_review`   | Security nit found during hotfix review  | Code Reviewer + human sign-off |
| `deferred_unblock`  | Deferred item promoted to blocking       | User triage + Orchestrator   |

---

## GAP-I2 Protocol Summary

| Gap   | What it prevents                              | Where enforced                                    |
|-------|-----------------------------------------------|---------------------------------------------------|
| I2-a  | Orchestrator routing without cross-check      | `orchestrator.agent.md §1` — run `junai pipeline next` and compare |
| I2-b  | Double-advance (re-advancing a complete stage) | `pipeline_runner.py advance` — idempotency guard  |
| I2-c  | Agent writing fields it doesn't own           | All 9 executing agents `§8` — scope restriction block |

---

## 9 Common Pipeline Scenarios

### S-1  Fresh feature start
```
junai pipeline init --project "ServeSight" --feature "chat-widget"
# → Orchestrator takes current_stage=intent
# → Intent agent → junai pipeline advance --event intent_complete
```

### S-2  Check where you are
```
junai pipeline status        # JSON: current_stage, mode, blocked_by
junai pipeline next          # shows next transition without advancing
```

### S-3  Re-enter a stalled pipeline (GAP-I6 drift resync via §9.2)
```
junai pipeline status        # confirm current_stage
# Orchestrator §9.2: detect drift, classify, confirm, advance
junai pipeline advance --event <stage>_complete --stage <stage>
```

### S-4  Satisfy a gate and unblock
```
junai pipeline status        # shows blocked_by: pre_deploy
junai pipeline gate --name pre_deploy
junai pipeline status        # blocked_by: null
```

### S-5  Switch to assisted or autopilot
```
junai pipeline mode --value assisted    # auto-routes, gates still require your approval
junai pipeline mode --value autopilot   # auto-routes + gates auto-satisfied (beta)
# Orchestrator invokes handoffs without waiting for button clicks
```

### S-6  Hotfix fast-track
```
junai pipeline init --project "ServeSight" --feature "null-crash" --type hotfix
# Orchestrator §12 activates: intent → implement → tester → closed
# Review only if security nit found
```

### S-7  Tester retry loop (up to 3×)
```
# Tester emits tester_result.status: failed
# Orchestrator routes back to Implement with failures[] in handoff
# After 3 failures: blocked_by: tester_retry_limit → human action required
```

### S-8  Scaffold and onboard a new agent
```
junai agent make --name my-agent --role executing
# edit TODO sections
junai agent validate --name my-agent
junai agent diff     --name my-agent
junai agent onboard  --name my-agent --yes
# add stage entry to agents.registry.json manually
junai agent inspect  --name my-agent
```

### S-9  Audit all agents
```
junai agent list     # shows: registered, §8, hard-stop, I2-c, role for all agents
# fix any NO entries via: junai agent onboard --name <agent-with-gaps>
```

---

## Recovery Paths

| Symptom                                   | First command to run               | Protocol                         |
|-------------------------------------------|------------------------------------|----------------------------------|
| Pipeline stuck, `blocked_by` set          | `junai pipeline status`            | Identify gate, `junai pipeline gate --name <g>` |
| Stage shows `in_progress` unexpectedly    | `junai pipeline next`              | Orchestrator §9.2 drift resync   |
| Advance returned "already complete"       | `junai pipeline status`            | I2-b guard triggered — normal; check artefact |
| Agent wrote wrong field (I2-c violation)  | `git diff pipeline-state.json`     | Manually revert to correct state, re-run |
| No `_routing_decision` in state           | `junai pipeline next --event <e>`  | Orchestrator §9 or §9.2 re-entry |
| `tester_retry_limit` gate raised          | `junai pipeline status`            | Human diagnosis; fix root cause; satisfy gate |

---

## File Locations

| File                                      | Purpose                                           |
|-------------------------------------------|---------------------------------------------------|
| `.github/pipeline-state.json`             | Live pipeline state (project-specific)            |
| `.github/pipeline-state.template.json`    | Blank template for new features (junai pool)      |
| `.github/pipeline/agents.registry.json`   | Stage→agent mapping, transition table             |
| `tools/pipeline-runner/pipeline_runner.py`| State machine engine                              |
| `tools/pipeline-runner/agent_manager.py`  | Agent lifecycle manager                           |
| `tools/pipeline-runner/junai.py`          | CLI dispatcher                                    |
| `junai.bat` / `junai.sh`                  | Shell entry points                                |
| `.github/agents/orchestrator.agent.md`    | Orchestrator routing logic                        |

---

*Generated: 2026-02-22 — JUNAI pipeline v1 (post-GAP-I2/I3/I4/I5/I6 + autopilot mode)*
