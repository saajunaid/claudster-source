---
description: End-of-session handoff — capture exact state so the next session resumes with zero re-discovery
---

# /handoff — stop cleanly, write the resume doc

You are ending a work session. Produce/refresh the resume doc (`.claudster/relay.md`) so the next session
(you, a future you, or another agent on any tool) can resume immediately. This is the anti-context-rot checkpoint.

## Step 1 — capture learnings FIRST (knowledge-transfer)
**Before** gathering git signals or writing relay.md, decide on `knowledge-transfer` — and the default
is to run it.

- **Trigger (default ON):** if this session's `git diff` touched any code or config, OR you debugged
  anything / proved a non-obvious behavior → you **MUST** dispatch the `knowledge-transfer` subagent first.
- **Skip ONLY if** the session was purely read-only, design/planning, or discussion — nothing was built,
  fixed, or proven. When in doubt, dispatch. "I already wrote some docs by hand" is **not** a reason to
  skip — the subagent routes/consolidates across the right files and catches what you'd miss.
- It writes durable findings (root causes, workarounds, constraints, rejected approaches) into the right
  CLAUDE.md / instructions / runbooks. Docs only — never code.
- **Record the outcome** in relay.md's `## Learnings captured` line (below). A skip must state its reason.

## Step 2 — gather verified signals (don't guess)
```
git status --short
git branch --show-current
git log --oneline -5
```
Then read the active plan in `.claudster/plans/` (falling back to legacy `.github/plans/` if present) and its tracker.

## Step 3 — write the resume doc (overwrite) with exactly these sections
> **Where to write:** solo / single active branch → `.claudster/relay.md` (default).
> **Team / parallel branches** → write `.claudster/relay/<current-branch>.md` instead, so two
> developers never merge-conflict on one shared relay doc. The SessionStart hook prefers the
> per-branch file automatically when it exists, then `.claudster/relay.md`, then the legacy
> `.claude/relay/<branch>.md` and root `relay.md` (back-compat during the migration).

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
- `.claudster/plans/<feature>.md` — the plan + tracker

## Validation state
<Commands run this session and their result: pass / fail / not-run. Be honest.>

## Open questions / blockers
<Decisions needed, ambiguities, anything unverified. "None" if truly none.>

## Learnings captured
knowledge-transfer: <✓ ran → files written | ✗ skipped → reason>

## Resume prompt
\`\`\`
Read relay.md, then the plan it points to. Continue from <phase/step>. Next action: <exact>.
\`\`\`
```

## Rules
- Only verified facts and real paths. Mark anything unconfirmed as `Unknown`.
- Update the plan's tracker rows too (status + last commit) — relay and tracker must agree.
- Don't commit unless asked. Report where `relay.md` was written and the one next action.
- **Prune the Done section — two rules, both apply:**
  1. **Merge-based:** Phases already merged to `main` (confirmed by a tag or commit) must be compressed
     to a single line: `- **RW-N**: merged to main as vYYYY.MM.DD.N (<commit>) ✅`. Only the current
     in-progress phase keeps detailed bullets.
  2. **Count-based:** The Done section must contain at most **8 bullets total** after writing. If there
     are more, collapse the oldest into one summary line:
     `- [N prior milestones — see git log for full history]`
     Keep the 8 most recent bullets below it.
  Target: relay.md stays under ~80 lines on disk. inject_relay.py caps injection at 120 lines as a
  safety net, but the file itself should never reach that ceiling.
