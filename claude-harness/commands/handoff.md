---
description: End-of-session handoff — capture exact state so the next session resumes with zero re-discovery
---

# /handoff — stop cleanly, write the resume doc

You are ending a work session. Produce/refresh `relay.md` at the repo root so the next session (you, a
future you, or another agent on any tool) can resume immediately. This is the anti-context-rot checkpoint.

## Gather verified signals (don't guess)
```
git status --short
git branch --show-current
git log --oneline -5
```
Then read the active plan in `.github/plans/` and its tracker.

## Write `relay.md` (overwrite) with exactly these sections
```markdown
# Relay — <feature>
**Updated:** <ISO timestamp>

## Current workstream
<Active plan path + which phase. One line on the goal.>

## Done (this session / across sessions)
- <evidence-backed bullet — cite file/commit, only what's actually complete>

## Next step (exact)
<The single next action. Include the command/phase. Add a fallback if blocked.>

## Read first on resume
- `<path>` — why it matters
- `.github/plans/<feature>.md` — the plan + tracker

## Validation state
<Commands run this session and their result: pass / fail / not-run. Be honest.>

## Open questions / blockers
<Decisions needed, ambiguities, anything unverified. "None" if truly none.>

## Resume prompt
\`\`\`
Read relay.md, then the plan it points to. Continue from <phase/step>. Next action: <exact>.
\`\`\`
```

## Step 0 — capture learnings first (knowledge-transfer)
Before writing relay.md, dispatch the `knowledge-transfer` subagent if any non-trivial
implementation or debugging happened this session. It writes durable findings (root causes,
workarounds, constraints) into the right CLAUDE.md / instructions files so docs stay current.
Skip if the session was read-only, design-only, or nothing non-obvious emerged.

## Rules
- Only verified facts and real paths. Mark anything unconfirmed as `Unknown`.
- Update the plan's tracker rows too (status + last commit) — relay and tracker must agree.
- Don't commit unless asked. Report where `relay.md` was written and the one next action.
- **Prune the Done section.** Phases already merged to `main` (confirmed by a tag or commit) must be
  compressed to a single line: `- **RW-N**: merged to main as vYYYY.MM.DD.N (<commit>) ✅`. Only the
  current in-progress phase keeps detailed bullets. This prevents relay.md from growing unboundedly
  across long projects — a 200-line relay.md injected twice at session start is a major context bloat
  source.
