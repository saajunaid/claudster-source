---
description: "Advisory Mode Boundary — rules for GitHub Copilot in advisory/planning chat"
applyTo: "**"
---

# Advisory Mode Boundary

When GitHub Copilot is used in an advisory or planning conversation (not operating as a named agent), these boundaries are **absolute and non-negotiable**.

## What advisory chat must NEVER do

- Edit files, run terminal commands, or make any code changes — those belong to a specialist agent in the project
- Compose **pipeline stage handoff prompts** — any prompt driven by `pipeline-state.json` phase numbers is `@Orchestrator`'s sole responsibility
- Route directly to a pipeline agent by constructing the full phase brief, even when the next step seems obvious

## What advisory chat is ALLOWED to do

- Read, explain, and reason about the codebase and pipeline state
- Diagnose a bug or symptom raised by the user in this conversation and produce a **Diagnostic Brief** for the appropriate specialist agent

## The decision gate — apply before composing any prompt

> **"Did I need to read `pipeline-state.json` to construct this prompt?"**
>
> - **YES** — Pipeline handoff. STOP. Say:
>   *"Go to @Orchestrator in a new session and say: '[one-line phrase describing the situation]'."*
>   Do not write the full prompt.
>
> - **NO** — Standalone issue raised in this conversation. Proceed with a **Diagnostic Brief**.

## Diagnostic Brief format

Use only when ALL of these are true:
1. The trigger is a symptom described by the user in this conversation
2. You have diagnosed (or can diagnose) the root cause from available context
3. A specialist agent is needed (`@debug`, `@security-analyst`, `@accessibility`, etc.)
4. The issue is NOT a scheduled pipeline stage

A Diagnostic Brief must contain:
1. **Diagnosed issue** — what is wrong and why (root cause)
2. **Evidence** — specific file, line number, or observed behaviour
3. **Agent to use** — which specialist to open in the project workspace
4. **Files to attach** — which files to bring into that agent's session
5. **Targeted prompt** — a concise statement of the specific problem to paste into the agent

A Diagnostic Brief must NOT:
- Reference `pipeline-state.json` phase numbers or pipeline stage names
- Replace `@Orchestrator` routing decisions
- Contain a full copy-paste phase implementation brief

## Session Mechanics — by Pipeline Mode

These rules apply in production and must NOT be baked into `orchestrator.agent.md` or any agent definition — they are routing meta-rules, not agent behaviour.

### Supervised mode
- Orchestrator presents a **handoff button (`send: false`)**; the user must click to approve the routing decision and send context to the specialist.
- Specialist completes work → presents **Return to Orchestrator button** → user clicks to begin the next routing cycle.
- **Start a new session** when returning to Orchestrator after a completed stage — keeps Orchestrator's context clean.
- **Pattern:** `@Orchestrator` (new session) → user clicks button → `@specialist` (same session) → user clicks Return → new session for next cycle.

### Assisted / Autopilot mode
- Orchestrator **invokes the specialist directly** via VS Code auto-routing (no button click needed).
- Specialist completes work → **invokes `@Orchestrator` directly** via VS Code auto-routing (no button click needed).
- The loop `Orchestrator → Specialist → Orchestrator → ...` runs without user intervention for autopilot; assisted pauses at supervision gates only.
- **Do NOT start a new session** between cycles in autopilot/assisted — the auto-routing chain preserves context across the full pipeline run.

## Auto-Routing Boundary (VS Code Copilot agent invocation)

VS Code Copilot can now automatically invoke named agents during a conversation without the user clicking a button. This capability does **not** change the advisory-chat boundary — it makes enforcing it more important.

**Advisory chat must NEVER auto-invoke a pipeline agent**, even when asked to:
- Auto-invoking a specialist agent (e.g. `@Implement`, `@Streamlit-Developer`) from outside Orchestrator **will not update `pipeline-state.json`**
- Work done via auto-routing from advisory chat is invisible to the pipeline — Orchestrator will re-do it or conflict with it on the next run
- There is no mechanism for advisory chat to call `satisfy_gate` — the pipeline state will be permanently at the wrong stage after the work is done

**When a user asks advisory chat to route to a specialist:**

> *"I can't do that directly — routing to a pipeline agent from here would cause pipeline state desync. Go to `@Orchestrator` and say: '[one-line task description]'. Orchestrator will check the state and route correctly."*

The only exception is a **Diagnostic Brief** for a bug raised in *this* conversation (non-pipeline work). A Diagnostic Brief does not advance pipeline stage, does not call MCP tools, and is explicitly labelled as outside the pipeline.

## Summary

All pipeline execution — regardless of how obvious the next step seems — routes through `@Orchestrator` in a new session. Advisory chat advises. Agents execute. Auto-routing from advisory chat to pipeline agents is explicitly prohibited.
