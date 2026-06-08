---
description: Capture requirements through structured discovery and write a PRD
argument-hint: <feature or problem>
---

# /prd — requirements discovery

Produce a Product Requirements Document for: **$ARGUMENTS**

If empty, ask what the feature/problem is and stop. Goal: turn a fuzzy idea into a crisp, testable spec
that `/feature-plan` can consume.

## Discovery (ask, don't assume)
Interview the user to fill gaps. Ask only what you can't infer from the codebase / `STACK.md`. Cover:
- **Problem & users** — what hurts, for whom, why now.
- **Outcome** — what "done" looks like in user terms; how we'd measure it.
- **Scope** — must-have vs nice-to-have vs explicitly out.
- **Data & constraints** — sources, fields, perf/security/compliance limits.
- **Edge cases & failure modes** — empty/error states, permissions.

Ask in small batches; stop interviewing once the spec is testable.

## Write to `.github/agent-docs/prd/<feature-slug>.md`
```markdown
# PRD — <feature>
**Created:** <ISO date>  •  **Status:** draft

## Problem
<who, what, why.>

## Goal & success criteria
- <measurable outcome>

## Functional requirements
- FR-1: <requirement — phrased so a test can verify it>

## Non-functional requirements
- NFR-1: <perf/security/a11y/...>

## Out of scope
- <explicitly excluded>

## Data
| Field / source | Shape | Notes |
|---|---|---|

## Edge cases & failure modes
- <empty / error / permission / boundary>

## Open questions
- <unresolved — needs a decision before planning>
```

## Report
Output the PRD path and the FR list. Suggest: *"Next: `/feature-plan <feature>`."* Don't design the
implementation here — PRD is the *what*, the plan is the *how*.
