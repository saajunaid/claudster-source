---
description: "Review project-local managed drift and promote selected reusable changes into a pool review branch"
mode: agent
tools: ['codebase', 'search', 'runCommands']
---

# /pool-promote

Use the pool promotion primitive instead of editing the pool manually.

## What to do

1. Run `junai pool diff --project <project-path>` and identify only reusable managed changes.
2. Keep the default choice conservative: if a change is not clearly reusable, keep it local.
3. Promote only the selected managed paths with `junai pool promote --project <project-path> --reason "<why this belongs in the pool>"`.
4. Stop on the created `promote/<project-name>-<YYYYMMDD>` branch and review it before any merge.
5. If the reusable change came from CI knowledge capture, use `junai pool nuggets review --project <project-path>` first so the durable lesson is written into a managed target before promotion.

## Rules

- Never promote `agent-docs/`, `handoffs/`, `plans/`, `.pool-version`, or other project-owned files.
- Never promote private or profile-excluded resources.
- For `copilot-instructions.md`, only the marker-managed region is promoted.
- Treat the promotion commit as provenance: include the source project and the reason.
- Do not auto-mirror project changes back to the pool outside this explicit review flow.
