---
description: "Emergency context handoff - for interruptions and unexpected situations"
mode: agent
tools: ['codebase', 'editFiles', 'search', 'runCommands']
---

# Context Handoff - Emergency Protocol

This prompt is **self-contained** — it does NOT depend on any external skill file.

## ⚠️ Before You Run This

**Is this the right tool?**

| Your Situation | Right Tool |
|----------------|------------|
| Large planned feature | ❌ Use a **plan document** with phases instead |
| Multi-session work | ❌ Use **phased execution** with plan doc |
| Interrupted mid-work | ✅ Use this handoff |
| Unexpected context exhaustion | ✅ Use this handoff |
| Handing to another person | ✅ Use this handoff |
| Checkpoint before risky change | ✅ Use this handoff |

**If you need a plan document instead:** Create a phased plan at `plans/<feature>.md` (in Cursor: use `/plan`; in other IDEs: use the [plan.prompt.md](plan.prompt.md) template).

---

## Execute Handoff

### Step 1: Determine Mode

| User Input | Mode |
|------------|------|
| `/context-handoff` | Auto-detect (FULL if >10 files changed or >5 tool calls, else QUICK) |
| `/context-handoff full` | Force FULL (document + prompt) |
| `/context-handoff quick` | Force QUICK (prompt only) |

**User's input**: `{{input}}`

### Step 2: Gather Context

Collect all of the following by reading the workspace:

1. **Run `get_changed_files()`** — get the full diff of staged + unstaged changes
2. **Read any active plan files** in `.github/plans/` — check status, phases, what's done/remaining
3. **Check the conversation history** — what was the user's original goal, what steps were completed
4. **List key files touched** — every file created, modified, or deleted in this session
5. **Note any errors, blockers, or decisions** — open issues, failing tests, design choices made

### Step 3: Generate Handoff Document

Create a markdown file at `.github/handoffs/YYYY-MM-DD_{task-name}.md` with this structure:

```markdown
# Context Handoff: {Task Name}

**Date**: {YYYY-MM-DD}
**Status**: {In Progress / Blocked / Near Complete}
**Plan Document**: {path to plan file, if any}

## What Was Being Done

{One paragraph describing the task and its goal}

## Current State

### Completed
- {List of completed items with file paths}

### In Progress
- {What was actively being worked on when interrupted}

### Not Started
- {Remaining items from the plan}

## Files Changed

| File | Action | Purpose |
|------|--------|---------|
| {path} | CREATE/MODIFY/DELETE | {brief description} |

## Key Decisions Made

| Decision | Rationale |
|----------|----------|
| {what was decided} | {why} |

## Blockers / Issues

- {Any errors, failing tests, or open questions}

## Test Status

- Last test run: {N passed, N failed, N skipped}
- Command: `{test command used}`

## Continuation Instructions

### Exact Next Step
{The precise action to take when resuming — be specific enough that a fresh agent can continue}

### Context Needed
{List any files the new session should read first to understand the current state}

### Continuation Prompt
```
{A ready-to-paste prompt the user can give to a new chat session to resume work}
```
```

### Step 4: Generate Continuation Prompt

Also output a ready-to-paste prompt block in the chat (not just in the file) that the user can copy into a new session. Format:

```
## Continuation Prompt (paste this in a new chat)

I'm resuming work on {task}. Read these files first:
1. {handoff document path}
2. {plan document path, if any}
3. {key files to read}

Current status: {one line summary}
Next step: {exact next action}
```

### Pipeline Boundary (when `pipeline-state.json` exists)

For pipeline-managed work, the continuation prompt must:

- Reference current state from `.github/pipeline-state.json`
- Avoid direct stage-routing instructions to non-orchestrator agents
- Avoid explicit gate toggles/state mutation instructions
- End with: "Open `@Orchestrator` in a new session and resume from pipeline state."

### Step 5: Git Checkpoint (optional)

If the project uses git, create a checkpoint:

```bash
git add -A && git commit -m "wip: checkpoint before handoff - {brief description}"
echo "{date} | {checkpoint-name} | $(git rev-parse --short HEAD)" >> .checkpoints.log
```

---

## Quick Reference

| Intent | Command |
|--------|--------|
| Auto (full or quick) | `/context-handoff` |
| Force full (document + prompt) | `/context-handoff full` |
| Quick (prompt only) | `/context-handoff quick` |

**Remember**: This is for emergencies. For planned large work, use phased execution with a plan document.

---

## Fallback: Minimal Quick Handoff

If for any reason the full process above cannot complete, capture these 5 things:

1. **What was being done**: One sentence describing the task
2. **Current state**: What's done, what's in progress, what's left
3. **Key files**: List the files modified or being worked on
4. **Blockers/issues**: Any errors, decisions needed, or unknowns
5. **Next action**: The exact next step to take when resuming

Save to `.github/handoffs/YYYY-MM-DD_{task-name}.md` AND output as a continuation prompt.

When resuming, verify the checkpoint:

```
CHECKPOINT VERIFICATION
=======================
Files changed since checkpoint: {count}
Tests passing: {pass}/{total}
Build status: PASS / FAIL
```

### Example Output

```markdown
## Handoff: Customer Search Feature (2026-02-09)

**Task**: Implement customer search with filters and pagination
**State**: Phase 2 of 3 complete. Backend API done. Frontend in progress.
**Git Checkpoint**: `abc1234` (branch: feature/customer-search)
**Files**: src/pages/Search.py (partial), src/services/search_service.py (done), src/components/search_filters.py (not started)
**Blockers**: Need to decide whether to use full-text search or LIKE queries for name matching
**Next**: Create search_filters.py component, then wire up to Search.py page
```
