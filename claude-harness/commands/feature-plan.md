---
description: Create a phased, TDD-structured implementation plan that acts as the durable spine for multi-session work
argument-hint: <feature description>
---

# /feature-plan — phased plan (the durable spine)

Create an implementation plan for: **$ARGUMENTS**

If `$ARGUMENTS` is empty, ask what to plan and stop.

The plan file is the **durable spine of the harness** — it must let any future session (or another
agent, on any tool) resume with zero re-discovery. Optimize for that.

## Step 1 — Scope check
Read the relevant code first (don't guess). If the work fits comfortably in one session, say so and
offer to just do it instead of planning. Only produce a plan for genuinely multi-phase work.

## Step 2 — Design phases
Break the work into **independently completable** phases (~30–60 min each, clear exit gate). Each phase
follows the harness loop: **RED → GREEN → REFACTOR → VERIFY → COMMIT**. Front-load risk.

Before writing the plan, consider dispatching the **preflight** subagent to validate your assumptions
(paths, symbols, APIs, primitives) against the codebase — it routinely catches wrong assumptions early.

## Step 3 — Write the plan to `.claudster/plans/<feature-slug>.md`

Create `.claudster/plans/` if it doesn't exist.

```markdown
---
type: plan
status: draft
feature: <feature-slug>
creation-agent: claudster
Original Author: Claude Code
Creation Date: <YYYY-MM-DDTHH:MM:SSZ>
Creating Model: <model-id>
---

# <Feature> — Implementation Plan
**Created:** <ISO date>  •  **Status:** Phase 1 of N  •  **Spine for:** <one-line goal>

## Goal
<2–3 sentences: what we're building and why.>

## Current state
<What exists now that's relevant — cite real files/symbols verified against the codebase.>

## Constraints & decisions
- <key tech decision + rationale>

## Phases

### Phase 1 — <name>  ⏳
**Goal:** <one sentence>
**Touches:** `<files>`
**TDD:**
  - RED: failing test(s) — `<test file>::<case>` asserting <behavior>
  - GREEN: <minimal implementation>
  - REFACTOR: <what to clean if needed>
**Verify (subagents):** dispatch `tester` (must return passed), then `code-reviewer` (verdict: approved)
**Exit gate:** <specific, testable — e.g. "GET /api/x returns 200 with {shape}", not "tests pass">
**Commit:** `<conventional commit message>`

### Phase 2 — <name>  🔲
<same structure>

## Affected files
| File | Action |
|---|---|

## Risks
| Risk | Mitigation |
|---|---|

## Tracker (update as you go — this is the resume signal)
| Phase | Status | Commit | Notes |
|---|---|---|---|
| 1 | not started | — | |
```

## Plan quality gate — local-coder ready (MANDATORY)
The plan must be executable by a **low-capability local coder model** (the planner→coder handoff: a
strong model plans, a cheaper/local model implements). The plan carries the intelligence; the coder
only follows it. Before finishing, verify every phase against this gate — a phase that fails it is not
done:
- **Exact paths** — every file to create/edit is named in full (no "the relevant service file").
- **Exact symbols** — function/class/component names and signatures are spelled out, not described.
- **Pre-decided judgment** — no "choose an approach", "use a suitable library", or open options left to
  the coder. If there's a decision, make it here with the rationale.
- **Explicit data bindings** — exact field paths / response shapes the code must read or produce.
- **Copy-paste verification** — each phase's exit gate is a literal command to run + expected output,
  not "tests pass".
- **No abbreviation** — never "etc.", "similar to Phase 1", "and so on". Write every item in full.

If any phase relies on the implementer *reasoning out* a gap, close the gap in the plan now.

## Step 4 — Report
Output the plan path (`.claudster/plans/<feature-slug>.md`), the phase list (one line each), confirm the
local-coder gate passed (or list the phases that need tightening), and: *"To start: `read the plan and
implement Phase 1`. To resume later: `/handoff` at session end, then `read relay.md` next time."*

Do not start implementing — this command only produces the plan.
