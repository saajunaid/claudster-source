---
description: "Create or update a root relay.md session-continuation document"
mode: agent
tools: ['codebase', 'editFiles', 'search', 'runCommands']
---

# /relay - Session Continuation Document

Create or update a generic `relay.md` file at the target repository root so a future session can quickly understand the project, the current workstream, and the exact next step.

This prompt is repository-agnostic. Do not assume a framework, branch strategy, documentation folder, plan folder, or application domain. Discover the current repository shape from files that actually exist.

## Input

User input: `{{input}}`

If the user names a specific task, workstream, branch, or plan, use it as the focus. If not, infer the most likely active workstream from the current conversation, changed files, visible project plans, and current repository state.

## Step 1: Inspect The Repository

Gather only verified facts. Prefer lightweight scans before reading large files.

1. Identify the repository root.
2. Check git state when available:
   - `git status --short`
   - `git branch --show-current`
   - `git log --oneline -5`
3. Read high-signal root files when present, such as `README.md`, `CHANGELOG.md`, `STACK.md`, package/build files, or project configuration files.
4. Search for active plans, roadmaps, TODO files, issue trackers, or architecture notes. Do not assume folder names; inspect what exists.
5. Identify validation commands from package scripts, makefiles, task runners, CI files, or documented commands.
6. Verify every file path before listing it in `relay.md`.

Do not invent paths, commands, phases, owners, or completion state. Mark unknowns explicitly.

## Step 2: Determine The Relay Context

Summarize:

- product or project goal
- current project context
- completed work that is visible from plans, docs, git history, or changed files
- current plan or workstream
- exact next step
- important files to read first
- validation state and commands
- blockers, assumptions, and open questions

If multiple plans exist, identify the active one by evidence: recent edits, checked-off progress, current user instruction, or current git changes. If the active plan is ambiguous, say so and list the likely candidates.

## Step 3: Create Or Update `relay.md`

Write the file at the repository root as `relay.md`.

### Metadata Source Rules

- Use full ISO 8601 UTC timestamps for `Creation Date` and `Last Updated`, for example `2026-05-21T13:30:00Z`.
- Use the exact current model identifier or display name from the chat/runtime model selector or session metadata for `Creating Model` and `Last Model Used`, for example `gpt-5.4`, `gpt-5.3-codex`, or `GPT-5.5`.
- Do not infer the model from the agent name, product name, or broad family. Generic agent, product, or family labels are not acceptable when the runtime exposes a precise model name.
- If the runtime does not expose an exact model identifier, record the most precise deterministic runtime identity available and say the exact ID was unavailable, for example `Codex (GPT-5-based; exact runtime model ID unavailable)`.

### New File Frontmatter

Use this frontmatter when `relay.md` does not exist:

```yaml
---
Original Author: <agent/user>
Creation Date: YYYY-MM-DDTHH:MM:SSZ
Creating Model: <exact runtime model identifier or display name>
---
```

### Existing File Frontmatter

When `relay.md` already exists:

1. Preserve the original `Original Author`, `Creation Date`, and `Creating Model` values.
2. Add or update the last-update fields above the original fields.
3. Use this order:

```yaml
---
Last Author: <agent/user>
Last Updated: YYYY-MM-DDTHH:MM:SSZ
Last Model Used: <exact runtime model identifier or display name>
Original Author: <preserved>
Creation Date: <preserved>
Creating Model: <preserved>
---
```

If an original field is missing in an existing file, preserve any available metadata and use `unknown` only for fields that cannot be recovered.

## Required Body Sections

Use exactly these top-level sections:

```
# Relay

## Purpose

## Current Project Context

## What Has Been Completed

## Current Plan Or Workstream

## Next Step

## Important Files To Read First

## Validation State

## Open Questions Or Blockers

## Resume Prompt
```

### Section Guidance

- `Purpose`: Explain why this relay file exists and what future sessions should use it for.
- `Current Project Context`: Summarize what the repository is for and the active direction.
- `What Has Been Completed`: List completed work with evidence where possible.
- `Current Plan Or Workstream`: Name the active plan, phase, issue, or branch if known.
- `Next Step`: Provide one concrete next action, plus a short fallback if the first action is blocked.
- `Important Files To Read First`: List only verified paths, with one-line reasons.
- `Validation State`: Include last known validation result and commands to run next. If not run, say not run.
- `Open Questions Or Blockers`: Include ambiguity, missing access, failing checks, or decisions needed.
- `Resume Prompt`: Provide a ready-to-paste prompt for a future agent inside a bare fenced code block. The opening fence must be exactly three backticks with no language label.

## Resume Prompt Requirements

The resume prompt must be self-contained and short enough to paste into a new session. It should tell the next agent to:

1. Read `relay.md` first.
2. Read the listed important files.
3. Continue from the named plan or workstream.
4. Run or preserve the listed validation commands as appropriate.
5. Avoid overwriting unrelated user changes.

Wrap the Resume Prompt content in triple backticks, but do not add a language label. The opening fence must be exactly three backticks and must not be labelled as `text`, `markdown`, or any other language.

## Step 4: Report Back

After writing `relay.md`, respond with:

- where the file was written
- the inferred current workstream
- the exact next step
- validation commands found or run
- any uncertainty that remains

Do not create commits unless the user explicitly asks.
