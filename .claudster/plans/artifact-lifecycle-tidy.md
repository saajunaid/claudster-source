---
type: plan
status: draft
feature: artifact-lifecycle-tidy
creation-agent: claudster
Original Author: Claude Code
Creation Date: 2026-07-22T00:00:00Z
Creating Model: claude-fable-5
---

# Artifact lifecycle tidy — plans/prompts auto-move to done/ in every repo

## Problem
`.claudster/plans/` and `.claudster/prompts/` accumulate finished artifacts. Moving them to `done/`
is manual, forgettable, and was done by hand twice this week. It should be a claudster behavior that
works in every repo the plugin serves.

## Design decisions (locked with the user, 2026-07-21; enum reconciled 2026-07-23)
1. **Frontmatter `status:` is the single source of truth**, per the canonical
   `document-frontmatter.instructions.md` contract (this convention is the lifecycle extension of
   that contract — the sibling of OKF-lite, which governs `.claudster/kb/` notes with `type:` only).
   - Terminal values: **`done` (canonical) and `superseded`**; `shipped` / `implemented` are accepted
     legacy synonyms treated as terminal (case-insensitive). Anything else — `draft`, `current`,
     `ready` — is active (`ready` = approved-and-waiting, NOT terminal).
   - Prompts are in the contract now (instruction updated 2026-07-23: `type: prompt`, prompts listed
     in scope) — new session-spec prompts are born with frontmatter; legacy frontmatter-less prompts
     are left alone by the mover and flagged by `--check`.
   - The implementing session flips the status — that already happens today; the move becomes
     mechanical.
2. **A deterministic script does the moving — never model judgment, never a mutating hook.** With
   multiple concurrent sessions per repo, a background hook that moves files mid-session is a race.
   A command-invoked script is predictable and testable.
3. **Trigger = the existing end-of-session rituals**, not a new command: `/claudster:handoff` and
   `/claudster:implement` (after the final phase) call the script. Optionally a `SessionEnd`/relay
   hook may PRINT a reminder when terminal-status files sit outside `done/` — visibility only, no moves.

## Phases

### Phase 1 — `claudster_tidy.py` (TDD)
**Touches:** `claude-harness/scripts/claudster_tidy.py` (new), `scripts/tests/test_claudster_tidy.py` (new).
**Behavior:**
- Scan `.claudster/plans/*.md` and `.claudster/prompts/*.md` (top level only; `done/` excluded).
- Parse YAML frontmatter `status:`; terminal (`done`, `superseded`, plus legacy `shipped`/
  `implemented`, case-insensitive) → move to sibling `done/` (create if missing).
  Use `git mv` when the file is tracked (preserve history); plain move when untracked; never
  overwrite an existing `done/<name>` (report + skip).
- `--dry-run` (default when invoked with no args from a hook context) prints what WOULD move;
  `--apply` moves. Always report: moved / would-move / stale-suspects (all phases ✅ but status
  still active — report only, never auto-flip status).
- **`--check` mode — mechanical conformance for generated artifacts** (closes the template-vs-output
  gap: validate_pool guards the doc-generation *templates*, nothing guarded the *outputs*):
  every top-level plan/prompt must have frontmatter with a known `status:` enum value; legacy
  synonyms are warned (suggest `done`); frontmatter-less files are listed. Exit 1 on violations so
  it can gate CI/pre-push later; legacy prompts predating the convention may be grandfathered via
  a small allowlist constant rather than moved/edited retroactively.
- Exit 0 always in report mode; `--apply` exits 1 only on a real failure (e.g. collision).
**Tests:** terminal statuses (incl. `superseded` + legacy synonyms) move; active/draft/`ready` stay;
prompts without frontmatter stay silently in `--apply` but are flagged by `--check`;
collision skips with message; untracked files move without git; dry-run touches nothing;
stale-suspect (checkmarked but draft) is reported not moved.
**Commit:** `feat(harness): claudster_tidy — deterministic done/-folder lifecycle for plans+prompts`

### Phase 2 — wire the triggers
**Touches:** `claude-harness/commands/handoff.md`, `claude-harness/commands/implement.md`,
`.github/runtime-targets.json` (claude target `files:` entry so the script ships in the plugin).
**Implement:** one step appended to each command body: run the script `--apply` and include its
report in the command's output; on collision, surface it instead of failing the whole command.
Convention note in the handoff/implement text: "flip the artifact's `status:` before this step."
**Commit:** `feat(commands): handoff + implement run claudster_tidy at close`

### Phase 3 (optional) — reminder-only visibility
**Touches:** the SessionStart relay hook (or statusline) — if `claudster_tidy --dry-run` reports
pending moves, print one line ("N finished artifacts awaiting tidy — /handoff moves them").
Strictly read-only; skip if the hooks dir is owned by another in-flight session at build time.
**Commit:** `feat(hooks): tidy reminder on session start (read-only)`

## Non-goals
- No auto-flipping of `status:` (that is the implementing session's judgment call).
- No mutating hooks, no background moves, no per-repo configuration beyond the convention.
- No retro-tagging of historical prompts — they were moved by hand already; the convention applies
  going forward.

## Prompt
```
Read E:\Projects\claudster-source\.claudster\plans\artifact-lifecycle-tidy.md fully, then execute it
autonomously in E:\Projects\claudster-source. TDD Phase 1 first (tests red, then green); full suite
(python -m pytest scripts/tests/ claude-harness/hooks/tests/ -q --import-mode=importlib) +
python validate_pool.py after each phase; commit per phase, only your files; update this plan's
phases with ✅ + hash. Coordination: if a concurrent session owns claude-harness/commands or the
hooks dir (check .claudster/relay.md), do Phase 1 and mark 2/3 blocked-on-coordination.
```
