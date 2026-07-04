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

## Headless mode
When the invocation contains the marker **`HEADLESS RUN RULES`** (a docket runner / non-interactive
caller spawned this session — no human is present), the Discovery interview above is **suspended**.
Instead:
- **Do not interview and do not ask questions.** Never use AskUserQuestion, never pause for approval,
  never wait for input. Derive every answer from `$ARGUMENTS`, the card context supplied in the prompt,
  `STACK.md`, and the codebase.
- **Unresolved items are not blockers** — record each one as a bullet under the PRD's `## Open questions`
  section and keep going. A headless run always produces the artifact.
- **Honor the caller's output path and slug.** Write to the `artifact_dir`/`feature` slug the caller
  specifies (falling back to `.claudster/prd/<feature-slug>.md`); set `feature: <slug>` in the
  frontmatter to that same slug. The frontmatter shape is unchanged from the interactive flow.
- **End with exactly one fenced `json` highlights block** as the final output — nothing after it — so the
  runner can parse the result. Keep `summary` ≤ 280 chars; `open_questions` is the count of bullets you
  wrote under `## Open questions`:
  ```json
  {"artifact":"<artifact_dir>/<slug>.md","summary":"<=280 chars>","open_questions":<int>}
  ```

Everything else — the PRD template, frontmatter, and section structure below — is identical in both
modes; only the interview is skipped.

## Write to `.claudster/prd/<feature-slug>.md`
```markdown
---
type: prd
status: draft
feature: <feature-slug>
creation-agent: claudster
Original Author: Claude Code
Creation Date: <YYYY-MM-DDTHH:MM:SSZ>
Creating Model: <model-id>
---

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

Create `.claudster/prd/` if it doesn't exist.
