# /usage-review
**Window:** 30d (2026-06-20 – 2026-07-20)  ·  **Sessions:** 2  ·  fable: 100% · sonnet: 93%

| Metric | Value |
|---|---|
| Output tokens | 4.1M |
| Input + cache read | 2001.2M |
| Cache efficiency | 100% read from cache |
| Est. cost equiv. | $784.35 (estimate; edit rates in session_end.py) |

## Findings

### 🟡 [R2] You're using the heaviest model for 100% of your work

  All of your output this window ran on Opus or Fable — the models most likely to hit rate limits. For everyday tasks like coding, searching, and editing, Sonnet delivers the same results and uses less of your rate-limit quota.

  **Action:** Switch to Sonnet for day-to-day work: type `/model` and pick Sonnet. Keep Opus for planning, architecture decisions, and final reviews.

### 🟡 [R4] Most of your sessions are running very long

  2 of 2 sessions peaked above 150k tokens of context. Long contexts make Claude slower, consume more of your rate-limit, and can get truncated above 200k. This usually means work is piling up without clearing out old context.

  **Action:** Use `/compact` mid-task to summarise context without losing the thread. Use `/clear` when switching to a completely different task.

### 🟡 [R6] 1 subagent is running on Opus unnecessarily

  These subagents dispatched on Opus this window: `unknown`. Most subagents don't need Opus-level reasoning — Sonnet handles code review, preflight checks, and testing just as well at a lower rate-limit cost.

  **Action:** Pin these agents to `model: sonnet` in their frontmatter files.
  **[apply]** — tell Claude: _apply finding R6_

### ℹ️ [R0] Your usage this window

  2 sessions. All on Opus or Fable — the models most likely to hit rate limits. Actual rate-limit % (5h / weekly cap) is not stored locally.

  **Action:** Run `/usage` in Claude Code to see your real-time rate-limit status.

### ℹ️ [R3] Tip: save `max` effort for when it really matters

  Effort level is not recorded in transcripts, so this is a general tip rather than a measured finding. `max` effort burns rate-limit quota significantly faster than `high` — reserve it for complex planning and architecture decisions. For regular coding, `high` is sufficient; for searches and quick edits, `medium` is fine.

  **Action:** Before each task, ask: does this actually need `max`? For most coding tasks, `high` is the right call.

## Agent dispatches this window

- `claudster:tester` × 22
- `claudster:ui-design-reviewer` × 17
- `claudster:code-reviewer` × 15
- `Explore` × 5
- `claudster:preflight` × 2
- `unknown` × 1 (on opus)

## Skills fired this window

- `playwright` × 23
- `claudster:feature-plan` × 2
- `frontend-design` × 1

---

## Notes for the claudster-source run

Investigated the R6 [apply] target against the installed agent frontmatter:

- `tester` — already `model: sonnet` (no change needed)
- `preflight` — already `model: sonnet`
- `code-reviewer` — `model: inherit` (inherits the main-loop model; this is the likely source of the "unknown on opus" dispatch R6 flagged)

R6's own target is `unknown`, which maps to no named agent file, so there is nothing cleanly auto-applicable. **Applied 2026-07-21:** pinned `code-reviewer` to `model: sonnet`. Corrected target — the note's original `plugin/agents/code-reviewer.md` does not exist; the file the Claude profile actually ships (per `runtime-targets.json`) and that carried the `model: inherit` causing the Opus dispatch is **`claude-harness/agents/code-reviewer.md`** (git-tracked, hand-maintained; the parallel `.github/agents/code-reviewer.agent.md` Copilot source was already `Sonnet 4.6`). Ships on the next `junai-push`.
